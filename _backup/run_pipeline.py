# run_pipeline.py 置き換え版
import argparse, os, sys, subprocess

def run(cmd):
    print("[RUN]", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--site", required=True, choices=["dk","fd"])
    p.add_argument("--input", required=True, help="raw DK/FD salaries or converted players CSV")
    p.add_argument("--output", required=True, help="final players_list.csv")
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # 1) 入力が “dk_players_SAMPLE.csv” でなければ変換（= サラリーCSV想定）
    if os.path.basename(args.input).lower() != "dk_players_sample.csv":
        converted = os.path.join(os.path.dirname(args.output), "dk_players_SAMPLE.csv")
        run([sys.executable, "convert_players_csv.py", "--site", args.site, "--input", args.input, "--out", converted])
        players_in = converted
    else:
        players_in = args.input

    # 2) players_list.csv を作成（make_dk_import.py が --out で書く前提）
    run([sys.executable, "make_dk_import.py", "--site", args.site, "--input", players_in, "--out", args.output])
    print("[OK] wrote", args.output)

if __name__ == "__main__":
    main()
