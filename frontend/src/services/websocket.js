export function connectWebSocket(onMessage, baseUrl) {
  const wsUrl = `${baseUrl.replace(/^http/, 'ws')}/ws`
  const ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    console.log('WebSocket conectado')
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
    setTimeout(() => connectWebSocket(onMessage, baseUrl), 3000)
  }

  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
  }

  return ws
}
