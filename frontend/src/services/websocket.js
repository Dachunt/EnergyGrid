export function connectWebSocket(onMessage, baseUrl, onStatusChange) {
  const wsUrl = `${baseUrl.replace(/^http/, 'ws')}/ws`
  let ws

  function connect() {
    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('WebSocket conectado')
      if (onStatusChange) onStatusChange(true)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (err) {
        console.error('Error parsing WS message:', err)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket desconectado, reconectando en 3s...')
      if (onStatusChange) onStatusChange(false)
      setTimeout(connect, 3000)
    }

    ws.onerror = (err) => {
      console.error('WebSocket error:', err)
    }
  }

  connect()

  return {
    close: () => { if (ws) ws.close() },
  }
}
