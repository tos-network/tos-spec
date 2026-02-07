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
MIN_TTL = 100
MAX_TTL = 86_400
MAX_ENCRYPTED_SIZE = 188
REGISTRATION_FEE = 10_000_000  # 0.1 TOS for name registration
BASE_MESSAGE_FEE = 5000  # 0.00005 TOS base ephemeral message fee
TTL_ONE_DAY = 28_800  # TTL threshold for fee tier 2

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

# Arbitration / Escrow / KYC
MIN_ARBITER_STAKE = COIN_VALUE * 1000
MAX_ARBITER_NAME_LEN = 128
MAX_FEE_BPS = 10_000
MAX_TASK_ID_LEN = 256
MAX_REASON_LEN = 1024
MAX_REFUND_REASON_LEN = 1024
MIN_TIMEOUT_BLOCKS = 10
MAX_TIMEOUT_BLOCKS = 525_600
MIN_APPEAL_DEPOSIT_BPS = 500
MAX_BPS = 10_000
MAX_ARBITRATION_OPEN_BYTES = 64 * 1024
MAX_VOTE_REQUEST_BYTES = 64 * 1024
MAX_SELECTION_COMMITMENT_BYTES = 64 * 1024
MAX_JUROR_VOTE_BYTES = 8 * 1024
APPROVAL_EXPIRY_SECONDS = 24 * 3600
APPROVAL_FUTURE_TOLERANCE_SECONDS = 3600
EMERGENCY_SUSPEND_TIMEOUT = 24 * 3600

MAX_COMMITTEE_MEMBERS = 21
MIN_COMMITTEE_MEMBERS = 3
MAX_APPROVALS = 15
EMERGENCY_SUSPEND_MIN_APPROVALS = 2
MAX_COMMITTEE_NAME_LEN = 128
MAX_MEMBER_NAME_LEN = 64
VALID_KYC_LEVELS = [0, 7, 31, 63, 255, 2047, 8191, 16383, 32767]

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
