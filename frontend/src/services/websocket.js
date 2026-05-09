export function connectWebSocket(onMessage) {
  const ws = new WebSocket('ws://localhost:8000/ws')

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
    setTimeout(() => connectWebSocket(onMessage), 3000)
  }

  ws.onerror = (err) => {
    console.error('WebSocket error:', err)
  }

  return ws
}
