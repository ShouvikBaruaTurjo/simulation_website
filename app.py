import random
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

# Banks et al. newsboy problem (Tables 2.x): newsday type and demand distributions
TYPES = ["Good", "Fair", "Poor"]
TYPE_P = [0.35, 0.45, 0.20]
DEMANDS = [40, 50, 60, 70, 80, 90, 100]
DEMAND_P = {
    "Good": [0.03, 0.05, 0.15, 0.20, 0.35, 0.15, 0.07],
    "Fair": [0.10, 0.18, 0.40, 0.20, 0.08, 0.04, 0.00],
    "Poor": [0.44, 0.22, 0.16, 0.12, 0.06, 0.00, 0.00],
}


def digit_ranges(probs):
    """Cumulative probabilities -> upper bounds on random digits 1..100 (100 = '00')."""
    cum, out = 0.0, []
    for p in probs:
        cum += p
        out.append(round(cum * 100))
    return out


def lookup(rd, probs, labels):
    for ub, lab in zip(digit_ranges(probs), labels):
        if rd <= ub:
            return lab
    return labels[-1]


def profit(demand, q, cost, price, scrap):
    sold = min(demand, q)
    revenue = sold * price
    purchase = q * cost
    lost = max(demand - q, 0) * (price - cost)   # lost profit from excess demand
    salvage = max(q - demand, 0) * scrap
    return revenue, purchase, lost, salvage, revenue - purchase - lost + salvage


def num(d, key, default, lo, hi):
    try:
        v = float(d.get(key, default))
    except (TypeError, ValueError):
        v = default
    return min(max(v, lo), hi)


def read_params(d):
    return dict(
        q=int(num(d, "q", 70, 0, 1000)),
        cost=num(d, "cost", 0.33, 0, 100),
        price=num(d, "price", 0.50, 0, 100),
        scrap=num(d, "scrap", 0.05, 0, 100),
    )


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.get("/api/config")
def config():
    return jsonify(
        types=[{"type": t, "p": p, "digits": r}
               for t, p, r in zip(TYPES, TYPE_P, digit_ranges(TYPE_P))],
        demands=DEMANDS,
        demand_p=DEMAND_P,
        demand_digits={t: digit_ranges(p) for t, p in DEMAND_P.items()},
    )


@app.post("/api/simulate")
def simulate():
    d = request.get_json(silent=True) or {}
    p = read_params(d)
    days = int(num(d, "days", 20, 1, 5000))
    seed = d.get("seed")
    rng = random.Random(int(seed)) if seed not in (None, "") else random.Random()
    rows, total = [], 0.0
    for day in range(1, days + 1):
        rd1, rd2 = rng.randint(1, 100), rng.randint(1, 100)
        t = lookup(rd1, TYPE_P, TYPES)
        dem = lookup(rd2, DEMAND_P[t], DEMANDS)
        rev, pur, lost, salv, pr = profit(dem, p["q"], p["cost"], p["price"], p["scrap"])
        total += pr
        rows.append(dict(day=day, rd1=rd1 % 100, type=t, rd2=rd2 % 100, demand=dem,
                         revenue=round(rev, 2), cost=round(pur, 2), lost=round(lost, 2),
                         salvage=round(salv, 2), profit=round(pr, 2)))
    return jsonify(rows=rows, total=round(total, 2), avg=round(total / days, 4))


if __name__ == "__main__":
    app.run(debug=True)
