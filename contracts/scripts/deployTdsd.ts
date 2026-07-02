import { compile, NetworkProvider } from "@ton/blueprint";
import { Address, toNano } from "@ton/core";

import {
  jettonContentCell,
  TdsdJettonMaster,
} from "../wrappers/TdsdJettonMaster";
import { envAddress, metadataUrl, optionalEnv } from "./env";

export async function run(provider: NetworkProvider) {
  const sender = provider.sender();
  const fallbackAdmin = sender.address;
  const adminAddress = optionalEnv("TDSD_OWNER_ADDRESS")
    ? envAddress("TDSD_OWNER_ADDRESS")
    : fallbackAdmin;

  if (!adminAddress) {
    throw new Error(
      "TDSD_OWNER_ADDRESS is required when the connected deploy wallet address is unavailable",
    );
  }

  const walletCode = await compile("TdsdJettonWallet");
  const masterCode = await compile("TdsdJettonMaster");
  const master = provider.open(
    TdsdJettonMaster.createFromConfig(
      {
        adminAddress,
        content: jettonContentCell(metadataUrl()),
        walletCode,
        totalSupply: 0n,
      },
      masterCode,
    ),
  );

  console.log("Deploying TDSD Jetton Master:", master.address.toString());
  console.log("Admin address:", adminAddress.toString());

  await master.sendDeploy(sender, toNano("0.07"));
  await provider.waitForDeploy(master.address);

  const data = await master.getJettonData();
  const projectOwner = optionalEnv("TDSD_PROJECT_WALLET_ADDRESS")
    ? envAddress("TDSD_PROJECT_WALLET_ADDRESS")
    : adminAddress;
  const projectJettonWallet = await master.getWalletAddress(projectOwner);

  printEnvSummary(master.address, projectJettonWallet, data.totalSupply);
}

function printEnvSummary(
  masterAddress: Address,
  projectJettonWallet: Address,
  totalSupply: bigint,
) {
  console.log("");
  console.log("TDSD deployed successfully.");
  console.log("Total supply:", totalSupply.toString());
  console.log("");
  console.log("Backend env:");
  console.log(`TDSD_JETTON_MASTER_ADDRESS=${masterAddress.toString()}`);
  console.log(`TDSD_PROJECT_JETTON_WALLET=${projectJettonWallet.toString()}`);
  console.log("TDSD_DEPOSITS_ENABLED=true");
}
