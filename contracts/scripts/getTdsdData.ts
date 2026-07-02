import { NetworkProvider } from "@ton/blueprint";

import { TdsdJettonMaster } from "../wrappers/TdsdJettonMaster";
import { TdsdJettonWallet } from "../wrappers/TdsdJettonWallet";
import { envAddress, optionalEnv } from "./env";

export async function run(provider: NetworkProvider) {
  const masterAddress = envAddress("TDSD_JETTON_MASTER_ADDRESS");
  const master = provider.open(TdsdJettonMaster.createFromAddress(masterAddress));
  const data = await master.getJettonData();

  console.log("TDSD Jetton Master:", masterAddress.toString());
  console.log("Total supply units:", data.totalSupply.toString());
  console.log("Mintable:", data.mintable);
  console.log("Admin:", data.adminAddress.toString());
  console.log("Content cell hash:", data.content.hash().toString("hex"));
  console.log("Wallet code hash:", data.walletCode.hash().toString("hex"));

  const owner = optionalEnv("TDSD_WALLET_OWNER")
    ? envAddress("TDSD_WALLET_OWNER")
    : undefined;
  if (!owner) {
    return;
  }

  const walletAddress = await master.getWalletAddress(owner);
  console.log("Owner:", owner.toString());
  console.log("Derived wallet:", walletAddress.toString());

  const wallet = provider.open(TdsdJettonWallet.createFromAddress(walletAddress));
  const walletData = await wallet.getWalletData();
  console.log("Wallet balance units:", walletData.balance.toString());
  console.log("Wallet owner:", walletData.ownerAddress.toString());
  console.log("Wallet master:", walletData.masterAddress.toString());
}
