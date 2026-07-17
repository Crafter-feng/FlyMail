/** WebSocket 连接管理：模块级单例 + 引用计数 + 多播监听
 *
 * 多个页面/组件调用 useWebSocket 时共享同一条 /ws 连接，
 * 避免同一标签开多条连接导致心跳与重连重复。
 */
import { ref, onUnmounted, type Ref } from 'vue'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

type MessageListener = (msg: WebSocketMessage) => void

// ---------- 模块级单例状态（全应用共享） ----------
let sharedSocket: WebSocket | null = null
const sharedConnected = ref(false)
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
// 指数退避重连：初始 3 秒，每次翻倍，最大 60 秒
let reconnectDelay = 3000
const MAX_RECONNECT_DELAY = 60000
// 引用计数：有组件需要连接时 >0，归零则真正断开
let refCount = 0
// 业务消息多播：各组件注册自己的 onMessage
const listeners = new Set<MessageListener>()

function clearReconnectTimer() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

function buildWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // 飞牛 OS 统一网关约定的 WebSocket 路径
  return `${protocol}//${window.location.host}/app/flymail/ws`
}

/** 真正建立底层 WebSocket（仅单例内部调用） */
function openSharedSocket() {
  if (sharedSocket) return
  if (refCount <= 0) return

  try {
    const socket = new WebSocket(buildWsUrl())

    socket.onopen = () => {
      sharedConnected.value = true
      reconnectDelay = 3000
    }

    socket.onmessage = (event) => {
      try {
        const data: WebSocketMessage = JSON.parse(event.data)
        // 服务端心跳：统一回复 pong，不往业务层抛
        if (data.type === 'ping') {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'pong' }))
          }
          return
        }
        // 多播给所有已注册监听器
        listeners.forEach((fn) => {
          try {
            fn(data)
          } catch {
            // 单个监听器异常不影响其他订阅者
          }
        })
      } catch {
        // 忽略非 JSON 消息
      }
    }

    socket.onclose = () => {
      sharedConnected.value = false
      sharedSocket = null
      // 仍有订阅者时自动重连
      if (refCount > 0) {
        clearReconnectTimer()
        reconnectTimer = setTimeout(() => {
          openSharedSocket()
        }, reconnectDelay)
        reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
      }
    }

    socket.onerror = () => {
      sharedConnected.value = false
    }

    sharedSocket = socket
  } catch {
    sharedSocket = null
    sharedConnected.value = false
    if (refCount > 0) {
      clearReconnectTimer()
      reconnectTimer = setTimeout(() => {
        openSharedSocket()
      }, reconnectDelay)
      reconnectDelay = Math.min(reconnectDelay * 2, MAX_RECONNECT_DELAY)
    }
  }
}

/** 释放一个引用；计数归零时断开连接 */
function releaseShared() {
  refCount = Math.max(0, refCount - 1)
  if (refCount > 0) return
  clearReconnectTimer()
  if (sharedSocket) {
    sharedSocket.onclose = null
    sharedSocket.close()
    sharedSocket = null
  }
  sharedConnected.value = false
  reconnectDelay = 3000
}

/**
 * 组件侧 API：注册监听 + 引用计数。
 * connect/disconnect 只增减引用，真正连/断由模块单例管理。
 */
export function useWebSocket(onMessage: (msg: WebSocketMessage) => void) {
  // 对外暴露与旧 API 兼容的 ref（指向共享连接状态）
  const ws = ref<WebSocket | null>(null) as Ref<WebSocket | null>
  const wsConnected = sharedConnected

  function connect() {
    listeners.add(onMessage)
    refCount += 1
    openSharedSocket()
    ws.value = sharedSocket
  }

  function disconnect() {
    listeners.delete(onMessage)
    releaseShared()
    ws.value = sharedSocket
  }

  // 组件卸载时自动减引用、移除监听
  onUnmounted(() => {
    disconnect()
  })

  return {
    ws,
    wsConnected,
    connect,
    disconnect,
  }
}
