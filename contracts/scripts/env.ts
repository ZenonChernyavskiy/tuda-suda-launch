import { Address } from "@ton/core";
import dotenv from "dotenv";

dotenv.config({ path: ".env.contracts" });
dotenv.config();

export function requiredEnv(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`${name} is required`);
  }
  return value;
}

export function optionalEnv(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value || undefined;
}

export function envAddress(name: string): Address {
  return Address.parse(requiredEnv(name));
}

export function envBigInt(name: string, fallback: bigint): bigint {
  const value = optionalEnv(name);
  return value ? BigInt(value) : fallback;
}

export function metadataUrl(): string {
  return requiredEnv("TDSD_METADATA_URL");
}
