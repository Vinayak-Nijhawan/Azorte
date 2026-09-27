# Prospectivity Model Results — Plain Language Report

---

## 1. One-line verdict

**"This model is weak but usable — it has learned real geological patterns, but it doesn't have enough examples of 'where manganese actually is' to be reliable yet."**

---

## 2. The 3 key numbers, explained simply

### Balanced Accuracy: 0.67 (67%)

Imagine you flip a coin to decide "is there manganese here or not?" A coin flip would be right 50% of the time. Our model gets it right about 67% of the time. That's clearly better than a coin flip, which proves it *has* learned something real from the geology and satellite data. But 67% also means it gets it wrong about 1 out of every 3 times, which isn't reliable enough for a company to spend lakhs of rupees drilling a borehole based on.

### PR-AUC: 0.03 (3%)

This one needs careful explanation. "PR-AUC" measures how well the model finds rare things. Think of it like this: manganese deposits are like needles in a haystack — only **17 out of 16,931 locations** (0.1%) in our dataset actually have manganese. A "perfect" needle-finder would score 1.0 (100%). A completely random guess would score about 0.001 (0.1%). Our model scored 0.03 (3%), which means **it's about 30 times better than random guessing at finding the needles**. That sounds impressive, but in absolute terms, it still means: if the model says "dig here, there's probably manganese," it will be wrong about 99 out of 100 times. The reason is simple — it only had 17 examples to learn from.

### ROC-AUC: 0.80 (80%)

This measures how good the model is at **ranking** — putting likely manganese locations above unlikely ones in a sorted list. A score of 0.50 means the ranking is no better than shuffling randomly. A score of 1.0 means perfect ranking. Our 0.80 means: **if you pick one random location that has manganese and one that doesn't, the model will correctly say "this one is more likely" about 80% of the time.** This is actually a decent score and shows the model has genuinely learned which rock types and geological features are associated with manganese.

---

## 3. Feature check

**`shear_zone_proximity_km` is ABSENT from the model.** Confirmed removed.

The top 3 real features driving predictions:

| Rank | Feature | Importance | What it means |
|------|---------|------------|---------------|
| 1 | `rock_type_encoded` | 17.4% | **Which rock is at that location** (from real NGDR Lithology). The model learned that certain rocks (like Schist, Calc Gneiss) are more associated with manganese. This is the single most important factor — exactly what a real geologist would say. |
| 2 | `clay_index` | 15.5% | **How much clay the satellite detected** on the surface (from real Sentinel-2). Clay minerals often form near metamorphic rocks that host manganese. |
| 3 | `fault_distance_km` | 13.9% | **How far from the nearest crack in the earth** (from real NGDR Fault lines). Manganese tends to concentrate near faults where hot fluids pushed minerals upward. |

> All 8 features contribute meaningfully (none is useless). The model is not dominated by any single feature, which is healthy.

---

## 4. The real-world test

If someone used this model today to decide where to physically go explore for manganese in Maharashtra or Madhya Pradesh, **it would point them in the broadly correct direction — toward the right rock types, near faults, in the right terrain — but it would also point them to many wrong spots.** Out of every 100 locations it flags as "high probability," roughly only 1 would actually have manganese. The reason isn't that the model is dumb; it's that we only gave it 17 real examples of "yes, manganese is here" out of 16,931 locations. That's like trying to teach someone to recognize a face after showing them only 17 photos out of a yearbook of 17,000 students. The model needs more positive examples to sharpen its aim.

---

## 5. What to do next

### Recommendation: **(B) It needs more positive-label data first.**

Here's exactly what's wrong and how to fix it:

**The Problem:**
Our satellite grid has points spaced roughly 2-10 km apart. But a manganese mining lease is often just a few hundred meters wide. So out of the 84 real lease polygons we downloaded from NGDR, only 17 of our grid points happened to land *inside* one. That's like throwing 17,000 darts at a wall and only 17 of them hit the 84 tiny bullseyes. The model can't learn properly from just 17 "yes" examples.

**The Fix (pick one or both):**

1. **Generate denser grid points around known mines (easiest, I can do this right now):**
   Instead of using the satellite grid as-is, I create extra grid points specifically inside and around each of the 84 manganese lease polygons (say, one point every 500 meters). This would give us 300-500+ positive examples instead of just 17, without downloading any new data.

2. **Download Odisha + Karnataka data from NGDR (adds more mining regions):**
   You already have MH + MP. If you also download Lithology + Fault + Lease data for Odisha (which has a huge manganese belt around Joda/Barbil), you'd add potentially 50+ more manganese lease polygons and thousands more grid points.

**My recommendation:** Option 1 is the fastest — I can implement it immediately and retrain within minutes. Want me to do it?
