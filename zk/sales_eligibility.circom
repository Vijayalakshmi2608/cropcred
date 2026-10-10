pragma circom 2.1.6;
include "node_modules/circomlib/circuits/comparators.circom";
template Main() {
  signal input sales;
  signal input threshold;
  signal output eligible;
  component comparison = LessEqThan(32);
  comparison.in[0] <== threshold;
  comparison.in[1] <== sales;
  eligible <== comparison.out;
}
component main {public [threshold]} = Main();
