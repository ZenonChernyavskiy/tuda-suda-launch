import {
  Address,
  beginCell,
  Cell,
  Contract,
  contractAddress,
  ContractProvider,
  Sender,
  SendMode,
  Slice,
  toNano,
} from "@ton/core";

export type TdsdJettonMasterConfig = {
  adminAddress: Address;
  content: Cell;
  walletCode: Cell;
  totalSupply?: bigint;
};

export const Opcodes = {
  mint: 21,
  burnNotification: 0x7bdd97de,
  provideWalletAddress: 0x2c76b973,
  takeWalletAddress: 0xd1735400,
};

export function jettonContentCell(metadataUrl: string): Cell {
  return beginCell()
    .storeUint(1, 8)
    .storeStringTail(metadataUrl)
    .endCell();
}

export function tdsdJettonMasterConfigToCell(config: TdsdJettonMasterConfig): Cell {
  return beginCell()
    .storeCoins(config.totalSupply ?? 0n)
    .storeAddress(config.adminAddress)
    .storeRef(config.content)
    .storeRef(config.walletCode)
    .endCell();
}

export class TdsdJettonMaster implements Contract {
  constructor(
    readonly address: Address,
    readonly init?: { code: Cell; data: Cell },
  ) {}

  static createFromAddress(address: Address): TdsdJettonMaster {
    return new TdsdJettonMaster(address);
  }

  static createFromConfig(
    config: TdsdJettonMasterConfig,
    code: Cell,
    workchain = 0,
  ): TdsdJettonMaster {
    const data = tdsdJettonMasterConfigToCell(config);
    const init = { code, data };
    return new TdsdJettonMaster(contractAddress(workchain, init), init);
  }

  async sendDeploy(provider: ContractProvider, via: Sender, value = toNano("0.05")) {
    return provider.internal(via, {
      value,
      sendMode: SendMode.PAY_GAS_SEPARATELY,
      body: new Cell(),
    });
  }

  async sendMint(
    provider: ContractProvider,
    via: Sender,
    args: {
      toOwner: Address;
      amount: bigint;
      forwardTonAmount?: bigint;
      value?: bigint;
      queryId?: bigint;
    },
  ) {
    const body = beginCell()
      .storeUint(Opcodes.mint, 32)
      .storeUint(args.queryId ?? 0n, 64)
      .storeAddress(args.toOwner)
      .storeCoins(args.amount)
      .storeCoins(args.forwardTonAmount ?? toNano("0.05"))
      .endCell();

    return provider.internal(via, {
      value: args.value ?? toNano("0.12"),
      sendMode: SendMode.PAY_GAS_SEPARATELY,
      body,
    });
  }

  async getJettonData(provider: ContractProvider): Promise<{
    totalSupply: bigint;
    mintable: boolean;
    adminAddress: Address;
    content: Cell;
    walletCode: Cell;
  }> {
    const result = await provider.get("get_jetton_data", []);
    return {
      totalSupply: result.stack.readBigNumber(),
      mintable: result.stack.readBoolean(),
      adminAddress: result.stack.readAddress(),
      content: result.stack.readCell(),
      walletCode: result.stack.readCell(),
    };
  }

  async getWalletAddress(provider: ContractProvider, owner: Address): Promise<Address> {
    const result = await provider.get("get_wallet_address", [
      { type: "slice", cell: beginCell().storeAddress(owner).endCell() },
    ]);
    return result.stack.readAddress();
  }
}

export function loadAddress(value: string | undefined, name: string): Address {
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return Address.parse(value);
}

export function addressToSlice(address: Address): Slice {
  return beginCell().storeAddress(address).endCell().beginParse();
}
