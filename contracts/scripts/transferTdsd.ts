import { NetworkProvider } from "@ton/blueprint";
import { Address, toNano } from "@ton/core";

import { TdsdJettonMaster } from "../wrappers/TdsdJettonMaster";
import {
  commentPayload,
  TdsdJettonWallet,
} from "../wrappers/TdsdJettonWallet";
import { envAddress, envBigInt, optionalEnv } from "./env";

export async function run(provider: NetworkProvider) {
  const sender = provider.sender();
  const senderOwner = optionalEnv("TDSD_TRANSFER_SENDER_OWNER")
    ? envAddress("TDSD_TRANSFER_SENDER_OWNER")
    : sender.address;

  if (!senderOwner) {
    throw new Error(
      "TDSD_TRANSFER_SENDER_OWNER is required when the connected wallet address is unavailable",
    );
  }

  const master = provider.open(
    TdsdJettonMaster.createFromAddress(envAddress("TDSD_JETTON_MASTER_ADDRESS")),
  );
  const senderJettonWalletAddress = await master.getWalletAddress(senderOwner);
  const senderJettonWallet = provider.open(
    TdsdJettonWallet.createFromAddress(senderJettonWalletAddress),
  );
  const destinationOwner = envAddress("TDSD_TRANSFER_DESTINATION_OWNER");
  const amount = envBigInt("TDSD_TRANSFER_AMOUNT_UNITS", 10n * 1_000_000_000n);
  const memo = optionalEnv("TDSD_TRANSFER_MEMO") ?? "TDSD test transfer";

  console.log("Transferring TDSD");
  console.log("Sender owner:", senderOwner.toString());
  console.log("Sender jetton wallet:", senderJettonWalletAddress.toString());
  console.log("Destination owner:", destinationOwner.toString());
  console.log("Amount units:", amount.toString());

  await senderJettonWallet.sendTransfer(sender, {
    amount,
    destinationOwner,
    responseDestination: sender.address ?? Address.parse(senderOwner.toString()),
    forwardTonAmount: 1n,
    forwardPayload: commentPayload(memo),
    value: toNano("0.1"),
  });
}
