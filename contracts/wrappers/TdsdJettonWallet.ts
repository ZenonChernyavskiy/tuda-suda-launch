import {
  Address,
  beginCell,
  Cell,
  Contract,
  ContractProvider,
  Sender,
  SendMode,
  toNano,
} from "@ton/core";

export const WalletOpcodes = {
  transfer: 0x0f8a7ea5,
  internalTransfer: 0x178d4519,
  transferNotification: 0x7362d09c,
  burn: 0x595f07bc,
  burnNotification: 0x7bdd97de,
  excesses: 0xd53276db,
};

export class TdsdJettonWallet implements Contract {
  constructor(readonly address: Address) {}

  static createFromAddress(address: Address): TdsdJettonWallet {
    return new TdsdJettonWallet(address);
  }

  async sendTransfer(
    provider: ContractProvider,
    via: Sender,
    args: {
      amount: bigint;
      destinationOwner: Address;
      responseDestination: Address;
      forwardTonAmount?: bigint;
      forwardPayload?: Cell;
      value?: bigint;
      queryId?: bigint;
    },
  ) {
    const body = beginCell()
      .storeUint(WalletOpcodes.transfer, 32)
      .storeUint(args.queryId ?? 0n, 64)
      .storeCoins(args.amount)
      .storeAddress(args.destinationOwner)
      .storeAddress(args.responseDestination)
      .storeMaybeRef(null)
      .storeCoins(args.forwardTonAmount ?? 1n)
      .storeRef(args.forwardPayload ?? new Cell())
      .endCell();

    return provider.internal(via, {
      value: args.value ?? toNano("0.08"),
      sendMode: SendMode.PAY_GAS_SEPARATELY,
      body,
    });
  }

  async sendBurn(
    provider: ContractProvider,
    via: Sender,
    args: {
      amount: bigint;
      responseDestination: Address;
      value?: bigint;
      queryId?: bigint;
    },
  ) {
    const body = beginCell()
      .storeUint(WalletOpcodes.burn, 32)
      .storeUint(args.queryId ?? 0n, 64)
      .storeCoins(args.amount)
      .storeAddress(args.responseDestination)
      .endCell();

    return provider.internal(via, {
      value: args.value ?? toNano("0.08"),
      sendMode: SendMode.PAY_GAS_SEPARATELY,
      body,
    });
  }

  async getWalletData(provider: ContractProvider): Promise<{
    balance: bigint;
    ownerAddress: Address;
    masterAddress: Address;
    walletCode: Cell;
  }> {
    const result = await provider.get("get_wallet_data", []);
    return {
      balance: result.stack.readBigNumber(),
      ownerAddress: result.stack.readAddress(),
      masterAddress: result.stack.readAddress(),
      walletCode: result.stack.readCell(),
    };
  }
}

export function commentPayload(text: string): Cell {
  return beginCell()
    .storeUint(0, 32)
    .storeStringTail(text)
    .endCell();
}
