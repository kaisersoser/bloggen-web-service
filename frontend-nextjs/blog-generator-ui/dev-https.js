const { createServer } = require('https')
const { parse } = require('url')
const next = require('next')
const fs = require('fs')
const path = require('path')

const dev = process.env.NODE_ENV !== 'production'
const app = next({ dev })
const handle = app.getRequestHandler()

const httpsOptions = {
  key: fs.readFileSync(path.join(__dirname, 'certs', 'localhost+2-key.pem')),
  cert: fs.readFileSync(path.join(__dirname, 'certs', 'localhost+2.pem')),
}

app.prepare().then(() => {
  createServer(httpsOptions, (req, res) => {
    const parsedUrl = parse(req.url, true)
    handle(req, res, parsedUrl)
  }).listen(3001, '0.0.0.0', (err) => {
    if (err) throw err
    console.log('🔒 HTTPS Server ready on:')
    console.log('   https://localhost:3001')
    console.log('   https://192.168.1.79:3001')
    console.log('   https://vogtcha-MS-7B12:3001')
  })
})
