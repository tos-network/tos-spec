"""TOS Python spec configuration constants.

Keep this file aligned with Rust constants in `common/src/transaction/*` and
`common/src/transaction/verify/*`.
"""

# Transaction limits
EXTRA_DATA_LIMIT_SIZE = 128
EXTRA_DATA_LIMIT_SUM_SIZE = EXTRA_DATA_LIMIT_SIZE * 32  # 4KB
MAX_TRANSFER_COUNT = 500
MAX_DEPOSIT_PER_INVOKE_CALL = 255
MAX_MULTISIG_PARTICIPANTS = 255
MAX_NONCE_GAP = 64
MAX_DELEGATEES = 500

# Units
COIN_DECIMALS = 8
COIN_VALUE = 10**COIN_DECIMALS

# Energy / freeze
MIN_FREEZE_TOS_AMOUNT = COIN_VALUE
MIN_UNFREEZE_TOS_AMOUNT = COIN_VALUE

# Privacy
MIN_SHIELD_TOS_AMOUNT = COIN_VALUE * 100

# TNS
MIN_NAME_LENGTH = 3
MAX_NAME_LENGTH = 64
REGISTRATION_FEE = 10_000_000  # 0.1 TOS for name registration

# TNS reserved names (names that cannot be registered)
RESERVED_NAMES = frozenset({
    "admin", "administrator", "system", "root", "null", "undefined",
    "tos", "tosnetwork", "test", "example", "localhost",
    "postmaster", "webmaster", "hostmaster", "abuse", "support", "info", "contact",
    "validator", "node", "daemon", "rpc", "api", "wallet", "bridge",
    "oracle", "governance", "treasury", "foundation", "network",
    "mainnet", "testnet", "devnet", "stagenet",
    "block", "transaction", "tx", "hash", "address",
    "security", "cert", "ssl", "tls", "www", "ftp", "mail",
    "smtp", "imap", "pop", "dns", "ntp", "ssh", "telnet", "ldap",
    "official", "verified", "authentic", "real", "true",
    "team", "staff", "mod", "moderator", "developer", "dev",
    "anonymous", "unknown", "nobody", "anyone", "everyone",
    "all", "none", "default", "guest", "user",
})

# TNS phishing keywords
PHISHING_KEYWORDS = ("official", "verified", "authentic", "support", "help")

# Contract limits
BURN_PER_CONTRACT = COIN_VALUE  # 1 TOS per contract deployed
MAX_GAS_USAGE_PER_TX = COIN_VALUE * 10  # 10 TOS max gas per transaction
TX_GAS_BURN_PERCENT = 30  # 30% of gas burned
MAX_VALUE_CELL_DEPTH = 64
MAX_ARRAY_SIZE = 10_000
MAX_MAP_SIZE = 10_000
MAX_BYTES_SIZE = 1_000_000
MAX_EVENTS_PER_TX = 1000
MAX_ERROR_RETURN_DATA = 4096

# Chain / network
CHAIN_ID_MAINNET = 0
CHAIN_ID_TESTNET = 1
CHAIN_ID_STAGENET = 2
CHAIN_ID_DEVNET = 3
