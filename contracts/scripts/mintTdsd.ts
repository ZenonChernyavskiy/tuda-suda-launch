import { NetworkProvider } from "@ton/blueprint";
import { toNano } from "@ton/core";

import { TdsdJettonMaster } from "../wrappers/TdsdJettonMaster";
import { envAddress, envBigInt } from "./env";

export async function run(provider: NetworkProvider) {
  const masterAddress = envAddress("TDSD_JETTON_MASTER_ADDRESS");
  const recipient = envAddress("TDSD_MINT_RECIPIENT");
  const amount = envBigInt("TDSD_MINT_AMOUNT_UNITS", 1_000n * 1_000_000_000n);

  const master = provider.open(TdsdJettonMaster.createFromAddress(masterAddress));

  console.log("Minting TDSD");
  console.log("Master:", masterAddress.toString());
  console.log("Recipient owner:", recipient.toString());
  console.log("Amount units:", amount.toString());

  await master.sendMint(provider.sender(), {
    toOwner: recipient,
    amount,
    value: toNano("0.15"),
    forwardTonAmount: toNano("0.05"),
  });
}
