const https = require('https');

const CONFIG = {
    email: 'alberto.kuang@gmail.com',
    password: 'Spring2025'
};

const LOGIN_URL = 'https://app.utrsports.net/api/v1/auth/login';
const SEARCH_URL = 'https://app.utrsports.net/api/v2/search/players';

function makeRequest(url, options = {}, postData = null) {
    return new Promise((resolve, reject) => {
        const urlObj = new URL(url);
        const req = https.request({
            hostname: urlObj.hostname,
            path: urlObj.pathname + urlObj.search,
            method: options.method || 'GET',
            headers: {
                'User-Agent': 'Mozilla/5.0',
                'Content-Type': 'application/json',
                ...options.headers
            }
        }, (res) => {
            let data = '';
            res.on('data', chunk => data += chunk);
            res.on('end', () => resolve({ status: res.statusCode, data: JSON.parse(data) }));
        });
        req.on('error', reject);
        if (postData) req.write(JSON.stringify(postData));
        req.end();
    });
}

async function main() {
    const loginRes = await makeRequest(LOGIN_URL, { method: 'POST' }, CONFIG);
    const token = loginRes.data.jwt;

    const searchRes = await makeRequest(`${SEARCH_URL}?top=1&gender=M`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    const player = searchRes.data.hits[0].source;
    console.log(JSON.stringify(player, null, 2));
}

main();
