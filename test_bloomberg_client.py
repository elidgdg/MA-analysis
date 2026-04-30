from ma_index_tracker.bloomberg_client import BloombergClient

def main() -> None:
    client = BloombergClient()

    ref = client.reference_data(
        security="NSC US Equity",
        fields=["NAME", "PX_LAST", "COUNTRY_ISO", "INDUSTRY_SECTOR"],
    )
    print("REFERENCE DATA:")
    print(ref)

    hist = client.historical_data(
        security="NSC US Equity",
        fields=["PX_LAST", "PX_VOLUME"],
        start_date="2025-07-20",
        end_date="2025-08-10",
    )
    print("\nHISTORICAL DATA:")
    print(hist[:5])

if __name__ == "__main__":
    main()