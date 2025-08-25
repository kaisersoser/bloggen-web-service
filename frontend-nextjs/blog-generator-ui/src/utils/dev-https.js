// Disable SSL verification for development (allows self-signed certificates)
process.env.NODE_TLS_REJECT_UNAUTHORIZED = '0';

const { createServer } = require('https')
const { parse } = require('url')
const next = require('next')
const fs = require('fs')
const path = require('path')

const dev = process.env.NODE_ENV !== 'production'
const app = next({ dev })
const handle = app.getRequestHandler()

const httpsOptions = {
  key: fs.readFileSync(path.join(__dirname, 'certs', 'localhost-new-key.pem')),
  cert: fs.readFileSync(path.join(__dirname, 'certs', 'localhost-new.pem')),
}

app.prepare().then(() => {
  createServer(httpsOptions, (req, res) => {
    const parsedUrl = parse(req.url, true)
    // Development fallback: some clients request '/layout.css' (missing the '/_next/static/css/app/' prefix)
    // which results in a 404. Provide a simple redirect to the real compiled CSS output.
    if (parsedUrl.pathname && parsedUrl.pathname === '/layout.css') {
      res.writeHead(302, { Location: '/_next/static/css/app/layout.css' })
      res.end()
      return
    }
    handle(req, res, parsedUrl)
  }).listen(3001, '0.0.0.0', (err) => {
    if (err) throw err
    console.log('🔒 HTTPS Server ready on:')
    console.log('   https://localhost:3001')
    console.log('   https://192.168.1.79:3001')
    console.log('   https://vogtcha-MS-7B12:3001')
  })
})
