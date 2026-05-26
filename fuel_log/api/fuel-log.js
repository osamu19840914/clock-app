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

async function fetchAllPages() {
  const results = [];
  let cursor = null;
  while (true) {
    const body = { page_size: 100 };
    if (cursor) body.start_cursor = cursor;
    const resp = await notionPost(`/v1/databases/${DATABASE_ID}/query`, body);
    results.push(...(resp.results || []));
    if (!resp.has_more) break;
    cursor = resp.next_cursor;
  }
  return results;
}

function getNumber(prop) {
  return prop && prop.type === 'number' ? prop.number : null;
}

function getDate(prop) {
  if (!prop) return null;
  if (prop.type === 'date' && prop.date)
    return prop.date.start.slice(0, 10);
  if (prop.type === 'title' && prop.title?.length)
    return (prop.title[0].plain_text || '').trim().replace(/\//g, '-') || null;
  if (prop.type === 'rich_text' && prop.rich_text?.length)
    return (prop.rich_text[0].plain_text || '').trim().replace(/\//g, '-') || null;
  return null;
}

function buildRecords(pages) {
  return pages.map(page => {
    const p    = page.properties || {};
    const date = getDate(p[PROP_DATE]);
    const fuel = getNumber(p[PROP_FUEL]);
    const dist = getNumber(p[PROP_DISTANCE]);
    if (!date || !fuel || !dist || fuel <= 0) return null;
    return {
      date,
      fuel:     Math.round(fuel * 100) / 100,
      distance: Math.round(dist * 100) / 100,
      kmpl:     Math.round(dist / fuel * 100) / 100,
    };
  }).filter(Boolean).sort((a, b) => a.date.localeCompare(b.date));
}

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json; charset=utf-8');

  if (!NOTION_TOKEN)  return res.status(500).json({ error: 'NOTION_TOKEN が設定されていません' });
  if (!DATABASE_ID)   return res.status(500).json({ error: 'NOTION_DATABASE_ID が設定されていません' });

  try {
    const records = buildRecords(await fetchAllPages());
    res.status(200).json(records);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
};
