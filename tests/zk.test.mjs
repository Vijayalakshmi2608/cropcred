import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { groth16 } from 'snarkjs';

const wasm = 'client/public/zk/sales_eligibility.wasm';
const zkey = 'client/public/zk/sales_eligibility_final.zkey';
const verificationKey = JSON.parse(await import('node:fs/promises').then((fs) => fs.readFile('client/public/zk/verification_key.json', 'utf8')));

async function prove(sales, threshold) {
  const result = await groth16.fullProve({ sales: String(sales), threshold: String(threshold) }, wasm, zkey);
  const verified = await groth16.verify(verificationKey, result.publicSignals, result.proof);
  return { ...result, verified };
}

const eligible = await prove(12, 10);
assert.equal(eligible.verified, true, 'valid eligible proof must verify');
assert.equal(eligible.publicSignals[0], '1', 'eligible condition must be true');
assert.equal(eligible.publicSignals[1], '10', 'threshold is the public signal');

const ineligible = await prove(3, 5);
assert.equal(ineligible.verified, true, 'valid ineligible proof must still verify cryptographically');
assert.equal(ineligible.publicSignals[0], '0', 'unsatisfied eligibility must be public as false');

const tampered = structuredClone(eligible.proof);
tampered.pi_a[0] = String(BigInt(tampered.pi_a[0]) + 1n);
assert.equal(await groth16.verify(verificationKey, eligible.publicSignals, tampered), false, 'tampered proof must fail');

await assert.rejects(() => groth16.fullProve({ threshold: '10' }, wasm, zkey), 'missing witness input must fail');

const fingerprint = (value) => crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
const passport = { verified_harvests: 12, completed_sales: 10, verified_payments: 10, verified_deliveries: 8 };
const originalFingerprint = fingerprint(passport);
const changedPassport = { ...passport, completed_sales: 11 };
assert.notEqual(fingerprint(changedPassport), originalFingerprint, 'changed passport data must invalidate its fingerprint');

console.log('Groth16 tests passed: valid, ineligible, tampered, malformed, and stale-fingerprint cases.');
