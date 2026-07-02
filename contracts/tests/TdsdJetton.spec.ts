import { Blockchain, SandboxContract, TreasuryContract } from "@ton/sandbox";
import { Cell, toNano } from "@ton/core";
import { compile } from "@ton/blueprint";
import "@ton/test-utils";

import {
  jettonContentCell,
  TdsdJettonMaster,
} from "../wrappers/TdsdJettonMaster";
import { TdsdJettonWallet } from "../wrappers/TdsdJettonWallet";

describe("TDSD Jetton", () => {
  let masterCode: Cell;
  let walletCode: Cell;
  let blockchain: Blockchain;
  let deployer: SandboxContract<TreasuryContract>;
  let user: SandboxContract<TreasuryContract>;
  let master: SandboxContract<TdsdJettonMaster>;

  beforeAll(async () => {
    walletCode = await compile("TdsdJettonWallet");
    masterCode = await compile("TdsdJettonMaster");
  });

  beforeEach(async () => {
    blockchain = await Blockchain.create();
    deployer = await blockchain.treasury("deployer");
    user = await blockchain.treasury("user");
    master = blockchain.openContract(
      TdsdJettonMaster.createFromConfig(
        {
          adminAddress: deployer.address,
          content: jettonContentCell("https://example.com/tdsd-metadata.json"),
          walletCode,
          totalSupply: 0n,
        },
        masterCode,
      ),
    );

    const deployResult = await master.sendDeploy(deployer.getSender(), toNano("0.1"));
    expect(deployResult.transactions).toHaveTransaction({
      from: deployer.address,
      to: master.address,
      deploy: true,
      success: true,
    });
  });

  it("exposes Jetton metadata and derives wallet addresses", async () => {
    const data = await master.getJettonData();
    expect(data.totalSupply).toEqual(0n);
    expect(data.mintable).toBe(true);
    expect(data.adminAddress.equals(deployer.address)).toBe(true);

    const walletAddress = await master.getWalletAddress(user.address);
    expect(walletAddress.toString()).toContain(":");
  });

  it("mints TDSD to a user wallet", async () => {
    const amount = 100n * 1_000_000_000n;
    const mintResult = await master.sendMint(deployer.getSender(), {
      toOwner: user.address,
      amount,
      value: toNano("0.2"),
      forwardTonAmount: toNano("0.05"),
    });

    expect(mintResult.transactions).toHaveTransaction({
      from: deployer.address,
      to: master.address,
      success: true,
    });

    const userWalletAddress = await master.getWalletAddress(user.address);
    const userWallet = blockchain.openContract(
      TdsdJettonWallet.createFromAddress(userWalletAddress),
    );
    const walletData = await userWallet.getWalletData();

    expect(walletData.balance).toEqual(amount);
    expect(walletData.ownerAddress.equals(user.address)).toBe(true);
    expect(walletData.masterAddress.equals(master.address)).toBe(true);
  });
});
