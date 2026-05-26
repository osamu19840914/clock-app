const https = require('https');

const NOTION_TOKEN  = process.env.NOTION_TOKEN  || '';
const DATABASE_ID   = process.env.NOTION_DATABASE_ID || '';
const PROP_DATE     = process.env.PROP_DATE     || '日付';
const PROP_FUEL     = process.env.PROP_FUEL     || '給油量';
const PROP_DISTANCE = process.env.PROP_DISTANCE || '走行距離';

function notionPost(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({
      hostname: 'api.notion.com',
      path,
      method: 'POST',
      headers: {
        'Authorization':  `Bearer ${NOTION_TOKEN}`,
        'Notion-Version': '2022-06-28',
        'Content-Type':   'application/json',
        'Content-Length': Buffer.byteLength(data),
      },
    }, (res) => {
      let raw = '';
      res.on('data', c => raw += c);
      res.on('end', () => { try { resolve(JSON.parse(raw)); } catch (e) { reject(e); } });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  try {
    const resp  = await notionPost(`/v1/databases/${DATABASE_ID}/query`, { page_size: 1 });
    const pages = resp.results || [];
    if (!pages.length) {
      return res.status(200).json({ message: 'データが0件。インテグレーションのDB接続を確認してください。' });
    }
    const propInfo = Object.fromEntries(
      Object.entries(pages[0].properties || {}).map(([k, v]) => [k, { type: v.type }])
    );
    res.status(200).json({
      env_settings: { PROP_DATE, PROP_FUEL, PROP_DISTANCE },
      notion_properties: propInfo,
      hint: 'notion_properties のキー名を環境変数 PROP_* に設定してください',
    });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
