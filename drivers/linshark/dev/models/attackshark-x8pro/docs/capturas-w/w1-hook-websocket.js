const _WS = window.WebSocket;
window.__log = [];
window.WebSocket = function (...a) {
  const ws = new _WS(...a);
  console.log("[asbridge-cap] WS open", a[0]);
  ws.addEventListener("message", e => window.__log.push({ dir: "rx", t: Date.now(), d: e.data }));
  const _send = ws.send.bind(ws);
  ws.send = d => { window.__log.push({ dir: "tx", t: Date.now(), d }); return _send(d); };
  ws.addEventListener("close", () => console.log("[asbridge-cap] WS close, frames=", window.__log.length));
  return ws;
};
console.log("[asbridge-cap] hook listo. Reconecta helper o recarga. Luego: copy(JSON.stringify(window.__log))");
