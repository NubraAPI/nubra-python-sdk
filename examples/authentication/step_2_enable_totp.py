from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

setup_client = InitNubraSdk(NubraEnv.UAT)
setup_client.totp_enable()
