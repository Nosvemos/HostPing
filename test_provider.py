import sys
import subprocess

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_provider.py \"Provider Name\"")
        print("Example: python test_provider.py \"Datalix Ryzen Gen4\"")
        sys.exit(1)

    provider_name = sys.argv[1]
    print(f"Testing selectors for provider: '{provider_name}'...")
    
    # Run scrapy crawl with test settings: LOG_LEVEL=WARNING, register TestPrintPipeline
    cmd = [
        "scrapy", "crawl", "dynamic_spider",
        "-a", f"target_provider={provider_name}",
        "-s", "ITEM_PIPELINES={\"hostping.pipelines.TestPrintPipeline\": 300}",
        "-s", "LOG_LEVEL=WARNING"
    ]
    
    subprocess.run(cmd)

if __name__ == "__main__":
    main()
