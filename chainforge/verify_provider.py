from chainforge.providers import ProviderRegistry
import chainforge.providers.native

print("Registry keys:", ProviderRegistry._registry.keys())
if "ollama" in ProviderRegistry._registry:
    print("SUCCESS: 'ollama' provider found.")
else:
    print("FAILURE: 'ollama' provider NOT found.")
