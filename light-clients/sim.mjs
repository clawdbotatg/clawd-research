import Colibri, { Strategy } from '@corpus-core/colibri-stateless';
const sent = [];
const f = globalThis.fetch;
const myFetch = async (u, o) => { const r = await f(u, o); sent.push(String(u).split('?')[0]); return r; };
const c = new Colibri({
  chainId: 1,
  prover: ['https://mainnet.colibri-proof.tech'],
  rpcs: [], include_code: true,
  prover_mode: process.env.MODE||'remote',
  proofStrategy: Strategy.VerifiedOnly,
  fetch: myFetch,
});
const USDC = '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
const vitalik = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045';
const t = async (label, fn) => { const s = Date.now(); try { const r = await fn(); console.log(label, Date.now()-s, 'ms', JSON.stringify(r, (k,v)=>typeof v==='bigint'?v.toString():v).slice(0, 900)); } catch (e) { console.log(label, 'ERR', Date.now()-s, 'ms', String(e.message||e).slice(0,400)); } };
await t('blockNumber', () => c.request({ method: 'eth_blockNumber', params: [] }));
await t('balance', () => c.request({ method: 'eth_getBalance', params: [vitalik, 'latest'] }));
await t('eth_call balanceOf', () => c.request({ method: 'eth_call', params: [{ to: USDC, data: '0x70a08231000000000000000000000000' + vitalik.slice(2) }, 'latest'] }));
// approve(spender = 0x1111..., max)
await t('simulate approve', () => c.request({ method: 'colibri_simulateTransaction', params: [{ from: vitalik, to: USDC, data: '0x095ea7b3' + '0000000000000000000000001111111254eeb25477b68fb85ed929f73a960582' + 'f'.repeat(64) }, 'latest'] }));

console.log('hosts:', [...new Set(sent.map(u => new URL(u).host))]);
console.log('requests:', sent.length);
process.exit(0);
