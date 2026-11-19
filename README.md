# duplicate-workorder-detector

When a room is too hot, three people call it in and the help desk opens three work orders. If each one goes to a vendor, the vendor is dispatched three times. This tool reads a work order CSV and flags pairs that describe the same job: same place, similar wording, opened within a few days of each other. It groups the pairs, names the earliest order as the one to keep, and lists the others for review. The sample data is synthetic.

## Install

```
git clone <this repository> && cd duplicate-workorder-detector
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Usage

```
python -m dupdetect data/work_orders.csv
```

Output:

```
20 work orders, 7 pairs, 5 duplicate groups

Group 1: keep WO-3001, review WO-3002
  Building A, Room 101 | Thermostat not responding

Group 2: keep WO-3004, review WO-3005
  Building B, Room 210 | Leaking faucet in restroom

Group 3: keep WO-3007, review WO-3008, WO-3009
  Building C, Room 305 | Ceiling tile stained and sagging

Group 4: keep WO-3014, review WO-3015
  Building B, Room 12 | Breaker tripping when heater runs

Group 5: keep WO-3018, review WO-3019
  Building D, Room 7 | Air handler noise

Pairs (score = 40% location + 60% description)
WO-3004 WO-3005  score 100.0  loc 100.0  desc 100.0  2 d apart
WO-3007 WO-3008  score 100.0  loc 100.0  desc 100.0  0 d apart
WO-3007 WO-3009  score 100.0  loc 100.0  desc 100.0  1 d apart
WO-3008 WO-3009  score 100.0  loc 100.0  desc 100.0  1 d apart
WO-3001 WO-3002  score  87.6  loc 100.0  desc  79.4  1 d apart
WO-3014 WO-3015  score  87.5  loc 100.0  desc  79.2  1 d apart
WO-3018 WO-3019  score  84.3  loc 100.0  desc  73.9  0 d apart
```

Options: `--location-min` (default 90), `--description-min` (default 70) and `--window` in days (default 14).

In the sample, WO-3010 and WO-3011 are the same problem in the same room 73 days apart. They are not flagged, because that is a repeat failure and not a double entry. WO-3001 and WO-3003 are not flagged because the rooms differ (101 and 102).

## How it works

- Text is lowercased, stripped of punctuation, and short forms are expanded (`bldg` to `building`, `rm` to `room`). Common filler words are removed from descriptions.
- Orders are sorted by date. For each order the scan looks forward only until the date window is passed.
- Tokens that contain a digit (room and building numbers) must be identical in both locations. This stops Room 101 from matching Room 102.
- The location score and description score come from the RapidFuzz `token_sort_ratio`, which ignores word order. A pair is flagged when both scores meet their minimum.
- Flagged pairs are merged into groups with union-find, so a three-way duplicate shows as one group.

## Limits

- It compares every order with later orders inside the date window. Fine for thousands of rows, slow for hundreds of thousands.
- Wording is judged by character similarity, not meaning. "No heat" and "Cold room" will not match.
- Two orders for different problems with similar text in the same room can be flagged. It is a review list, not an auto-close tool.
- Input needs the columns `id`, `location`, `description` and `created` (ISO date).

## License

MIT. Yassine Emhamed, 2026.
