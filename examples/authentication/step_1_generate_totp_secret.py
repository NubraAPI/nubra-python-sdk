from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

setup_client = InitNubraSdk(NubraEnv.UAT)
secret = setup_client.totp_generate_secret()
print("TOTP Secret:", secret)
