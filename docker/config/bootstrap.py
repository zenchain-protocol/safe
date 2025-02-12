import os

from chains.models import Chain, GasPrice, Feature
from django.core.management.base import BaseCommand
from safe_apps.models import Provider, SafeApp

TRANSACTION_SERVICE_TESTNET_URI = os.environ.get("TRANSACTION_SERVICE_TESTNET_URI")
if not TRANSACTION_SERVICE_TESTNET_URI:
    raise ValueError("The TRANSACTION_SERVICE_TESTNET_URI environment variable is not set.")

VPC_TRANSACTION_SERVICE_TESTNET_URI = os.environ.get(
    "VPC_TRANSACTION_SERVICE_TESTNET_URI", TRANSACTION_SERVICE_TESTNET_URI
)

class Command(BaseCommand):
    help = "Bootstrap configuration data"

    def handle(self, *args, **options):
        Chain.objects.all().delete()
        GasPrice.objects.all().delete()
        Provider.objects.all().delete()
        SafeApp.objects.all().delete()

        self._bootstrap_features()

        if Chain.objects.count() == 0:
            self._bootstrap_chain()

    def _bootstrap_features(self):
        self._feature_contract_interaction, _ = Feature.objects.get_or_create(key="CONTRACT_INTERACTION")
        self._feature_domain_lookup, _ = Feature.objects.get_or_create(key="DOMAIN_LOOKUP")
        self._feature_eip1559, _ = Feature.objects.get_or_create(key="EIP1559")
        self._feature_erc721, _ = Feature.objects.get_or_create(key="ERC721")
        self._feature_safe_apps, _ = Feature.objects.get_or_create(key="SAFE_APPS")
        self._feature_safe_tx_gas_optional, _ = Feature.objects.get_or_create(key="SAFE_TX_GAS_OPTIONAL")
        self._feature_spending_limit, _ = Feature.objects.get_or_create(key="SPENDING_LIMIT")

    def _bootstrap_chain(self):

        chain = Chain.objects.create(
            name="ZenChain Testnet",
            id="8408",
            description="",
            short_name="zentest",
            l2=False,
            rpc_authentication=Chain.RpcAuthentication.NO_AUTHENTICATION,
            rpc_uri="https://zenchain-testnet.api.onfinality.io/public",
            safe_apps_rpc_authentication=Chain.RpcAuthentication.NO_AUTHENTICATION,
            safe_apps_rpc_uri="https://zenchain-testnet.api.onfinality.io/public",
            public_rpc_authentication=Chain.RpcAuthentication.NO_AUTHENTICATION,
            public_rpc_uri="https://zenchain-testnet.api.onfinality.io/public",
            block_explorer_uri_address_template="https://zentrace.io/address/{{address}}/transactions",
            block_explorer_uri_tx_hash_template="https://zentrace.io/tx/{{txHash}}",
            block_explorer_uri_api_template="https://api.zentrace.io/api?module={{module}}&action={{action}}&address={{address}}&apiKey={{apiKey}}",
            currency_name="Unizen Exchange Token",
            currency_symbol="ZCX",
            currency_decimals=18,
            currency_logo_uri="https://safe-transaction-assets.gnosis-safe.io/chains/1/currency_logo.png",
            transaction_service_uri=TRANSACTION_SERVICE_TESTNET_URI,
            vpc_transaction_service_uri=VPC_TRANSACTION_SERVICE_TESTNET_URI,
            theme_text_color="#001428",
            theme_background_color="#E8E7E6",
            ens_registry_address=None,
            recommended_master_copy_version="1.3.0",
        )
        self._feature_contract_interaction.chains.add(chain)
        self._feature_domain_lookup.chains.add(chain)
        self._feature_eip1559.chains.add(chain)
        self._feature_erc721.chains.add(chain)
        self._feature_safe_apps.chains.add(chain)
        self._feature_safe_tx_gas_optional.chains.add(chain)
        self._feature_spending_limit.chains.add(chain)

        GasPrice.objects.create(
            chain_id=8408,
            oracle_uri=None,
            oracle_parameter=None,
            gwei_factor="100000000.000000000",
            fixed_wei_value=None,
        )