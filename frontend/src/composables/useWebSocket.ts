/** WebSocket 连接管理 composable，处理连接、重连、心跳 */
import { ref, onUnmounted } from 'vue'

export interface WebSocketMessage {
  type: string
  [key: string]: any
}

export function useWebSocket(onMessage: (msg: WebSocketMessage) => void) {
  const ws = ref<WebSocket | null>(null)
  const wsConnected = ref(false)
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  // 指数退避重连：初始3秒，每次翻倍，最大60秒
  let wsReconnectDelay = 3000
  const MAX_RECONNECT_DELAY = 60000

  /** 建立 WebSocket 连接 */
  function connect() {
    if (ws.value) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    // 飞牛 OS 统一网关约定的 WebSocket 路径
    const wsUrl = `${protocol}//${window.location.host}/app/flymail/ws`

    try {
      const socket = new WebSocket(wsUrl)

      socket.onopen = () => {
        wsConnected.value = true
        // 连接成功，重置重连延迟
        wsReconnectDelay = 3000
      }

      socket.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data)
          // 收到服务端心跳 ping，立即回复 pong 保持连接
          if (data.type === 'ping') {
            socket.send(JSON.stringify({ type: 'pong' }))
            return
          }
          // 非心跳消息交给业务回调处理
          onMessage(data)
        } catch {
          // 忽略非 JSON 消息
        }
      }

      socket.onclose = () => {
        wsConnected.value = false
        ws.value = null
        // 指数退避重连
        reconnectTimer = setTimeout(connect, wsReconnectDelay)
        wsReconnectDelay = Math.min(wsReconnectDelay * 2, MAX_RECONNECT_DELAY)
      }

      socket.onerror = () => {
        wsConnected.value = false
      }

      ws.value = socket
    } catch {
      // 连接创建失败，延迟重试
      reconnectTimer = setTimeout(connect, wsReconnectDelay)
      wsReconnectDelay = Math.min(wsReconnectDelay * 2, MAX_RECONNECT_DELAY)
    }
  }

  /** 断开 WebSocket 连接 */
  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.onclose = null // 阻止自动重连
      ws.value.close()
      ws.value = null
    }
    wsConnected.value = false
  }

  // 组件卸载时自动断开连接
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
