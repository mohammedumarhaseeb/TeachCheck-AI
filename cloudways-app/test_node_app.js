/**
 * Integration Test for Cloudways Node.js Application Server
 */

const http = require('http');

async function get(path) {
  return new Promise((resolve, reject) => {
    http.get(`http://127.0.0.1:3000${path}`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    }).on('error', reject);
  });
}

async function post(path, bodyObj = {}) {
  const postData = JSON.stringify(bodyObj);
  return new Promise((resolve, reject) => {
    const req = http.request(`http://127.0.0.1:3000${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on('error', reject);
    req.write(postData);
    req.end();
  });
}

async function runTests() {
  console.log('=== Testing TeachCheck AI Cloudways Node.js App ===');

  // 1. Health Endpoint
  const healthRes = await get('/api/health');
  console.log(`1. /api/health: HTTP ${healthRes.status}`);
  assert(healthRes.status === 200, 'Expected 200 from health endpoint');
  const health = JSON.parse(healthRes.body);
  assert(health.status === 'healthy', 'Expected status to be healthy');
  assert(health.model === 'gemma-4-26b-a4b-it', 'Expected model gemma-4-26b-a4b-it');
  assert(health.hasApiKey === true, 'Expected hasApiKey to be true');
  assert(!healthRes.body.includes('AIza'), 'SECURITY CHECK: API key must NEVER be in response');
  assert(!healthRes.body.includes('tc_internal'), 'SECURITY CHECK: Internal secret must NEVER be in response');
  console.log('   Health check & Security assertions: PASS');

  // 2. Static Frontend
  const indexRes = await get('/');
  console.log(`2. Static index.html: HTTP ${indexRes.status}`);
  assert(indexRes.status === 200, 'Expected 200 for index.html');
  assert(indexRes.body.includes('TeachCheck AI'), 'Expected page title/brand');
  assert(!indexRes.body.includes('AIza'), 'SECURITY CHECK: HTML must not contain API key');
  console.log('   Static frontend delivery: PASS');

  // 3. Demo Benchmark Analysis
  const demoRes = await post('/api/analyze-demo');
  console.log(`3. /api/analyze-demo: HTTP ${demoRes.status}`);
  assert(demoRes.status === 200, 'Expected 200 for demo analysis');
  const demo = JSON.parse(demoRes.body);
  assert(demo.success === true, 'Expected success: true');
  assert(demo.analysis.is_demo_mode === true, 'Expected is_demo_mode: true');
  assert(demo.analysis.model_used === 'gemma-4-26b-a4b-it', 'Expected model gemma-4-26b-a4b-it');
  assert(demo.analysis.findings.length === 6, 'Expected 6 findings');
  assert(demo.analysis.summary_metrics.total_issues === 2, 'Expected 2 issues');
  assert(demo.analysis.summary_metrics.confirmed_inconsistencies === 1, 'Expected 1 confirmed error');
  console.log('   Demo benchmark pipeline: PASS');

  console.log('=== Cloudways Node.js App Tests ALL PASSED! ===');
}

function assert(condition, message) {
  if (!condition) {
    console.error('FAIL:', message);
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error('Test Suite Error:', err);
  process.exit(1);
});

