import requests
import argparse
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed


import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def check_target(base_url, path, extensions, match_codes, follow_redirects, user_agent):
    results = []
    
    paths_to_test = [path] + [f"{path}{ext if ext.startswith('.') else '.' + ext}" for ext in extensions]

    headers = {"User-Agent": user_agent}

    for p in paths_to_test:
        full_url = f"{base_url.rstrip('/')}/{p.lstrip('/')}"
        try:
            response = requests.get(
                full_url,
                headers=headers,
                timeout=4.0,
                allow_redirects=follow_redirects,
                verify=False
            )
            
            status = response.status_code
            length = len(response.content)

            if status in match_codes:
                results.append({
                    "url": full_url,
                    "status": status,
                    "length": length,
                    "redirect": response.headers.get("Location", "")
                })

        except requests.exceptions.RequestException:
            pass

    return results

def main():
    parser = argparse.ArgumentParser(
        description="Komplexní HTTP Directory & File Scanner",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument("-u", "--url", required=True, help="Cílová URL (např. http://target.com)")
    parser.add_argument("-w", "--wordlist", required=True, help="Cesta k wordlistu")
    parser.add_argument("-t", "--threads", type=int, default=15, help="Počet vláken (výchozí: 15)")
    parser.add_argument("-x", "--extensions", type=str, default="", help="Přípony oddělené čárkou (např. php,html,txt)")
    parser.add_argument("-mc", "--match-codes", type=str, default="200,301,302,403", help="HTTP kódy k zobrazení (výchozí: 200,301,302,403)")
    parser.add_argument("-r", "--redirects", action="store_true", help="Následovat přesměrování (follow redirects)")
    parser.add_argument("-a", "--user-agent", type=str, default="ReconFramework/2.0", help="Vlastní User-Agent")
    parser.add_argument("-o", "--output", type=str, help="Cesta k souboru pro uložení výsledků (.json nebon .txt)")

    args = parser.parse_args()

    target_url = args.url if args.url.startswith(("http://", "https://")) else f"http://{args.url}"
    extensions = [ext.strip() for ext in args.extensions.split(",") if ext.strip()]
    match_codes = [int(code.strip()) for code in args.match_codes.split(",") if code.strip().isdigit()]

    try:
        with open(args.wordlist, "r", encoding="utf-8", errors="ignore") as f:
            words = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except Exception as e:
        print(f"[-] Chyba při načítání wordlistu: {e}")
        return

    print("=" * 70)
    print(f" Cíl:              {target_url}")
    print(f" Načteno slov:     {len(words)}")
    print(f" Testované přípony: {extensions if extensions else 'Žádné'}")
    print(f" Sledované kódy:   {match_codes}")
    print(f" Počet vláken:     {args.threads}")
    print("=" * 70 + "\n")

    start_time = time.time()
    discovered = []

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [
            executor.submit(
                check_target, 
                target_url, 
                word, 
                extensions, 
                match_codes, 
                args.redirects, 
                args.user_agent
            ) 
            for word in words
        ]

        for future in as_completed(futures):
            res_list = future.result()
            for res in res_list:
                discovered.append(res)
                redirect_info = f" -> {res['redirect']}" if res['redirect'] else ""
                print(f"[+] [{res['status']}]  Size: {res['length']:<8}  /{res['url'].replace(target_url, '').lstrip('/')}{redirect_info}")

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    print(f" Skenování dokončeno za {duration}s | Nalezeno položek: {len(discovered)}")
    print("=" * 70)

    if args.output and discovered:
        try:
            if args.output.endswith(".json"):
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(discovered, f, indent=4)
            else:
                with open(args.output, "w", encoding="utf-8") as f:
                    for item in discovered:
                        f.write(f"[{item['status']}] {item['url']} (Size: {item['length']})\n")
            print(f"[+] Výsledky byly úspěšně uloženy do: {args.output}")
        except Exception as e:
            print(f"[-] Chyba při zápisu do souboru: {e}")

if __name__ == "__main__":
    main()