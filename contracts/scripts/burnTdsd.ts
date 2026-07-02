import { NetworkProvider } from "@ton/blueprint";
import { Address, toNano } from "@ton/core";

import { TdsdJettonMaster } from "../wrappers/TdsdJettonMaster";
import { TdsdJettonWallet } from "../wrappers/TdsdJettonWallet";
import { envAddress, envBigInt, optionalEnv } from "./env";

export async function run(provider: NetworkProvider) {
  const sender = provider.sender();
  const owner = optionalEnv("TDSD_BURN_OWNER")
    ? envAddress("TDSD_BURN_OWNER")
    : sender.address;

  if (!owner) {
    throw new Error(
      "TDSD_BURN_OWNER is required when the connected wallet address is unavailable",
    );
  }

  const master = provider.open(
    TdsdJettonMaster.createFromAddress(envAddress("TDSD_JETTON_MASTER_ADDRESS")),
  );
  const walletAddress = await master.getWalletAddress(owner);
  const wallet = provider.open(TdsdJettonWallet.createFromAddress(walletAddress));
  const amount = envBigInt("TDSD_BURN_AMOUNT_UNITS", 1n * 1_000_000_000n);

  console.log("Burning TDSD");
  console.log("Owner:", owner.toString());
  console.log("Jetton wallet:", walletAddress.toString());
  console.log("Amount units:", amount.toString());

  await wallet.sendBurn(sender, {
    amount,
    responseDestination: sender.address ?? Address.parse(owner.toString()),
    value: toNano("0.1"),
  });
}
