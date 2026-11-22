# BidScout — Version 1

A static, mobile-friendly nationwide landscaping bid discovery **demo**. No frameworks, APIs, hosting fees, or build tools required.

## What works
- Search by title, category, city, state, or description
- Filter by service category and all 50 U.S. states
- Sort results by sample deadline, title, or state
- Save/unsave opportunities locally in your browser
- Responsive layout

## Important
Every listing is **fictional demo data**. This site does not connect to live bid sources, provide actual solicitation links, or verify deadlines. Do not advertise these listings as real. Saved items are stored only in the browser and do not sync across devices.

## Preview locally
Double-click `index.html` in a browser. Keep `styles.css` and `app.js` in the same folder.

## Publish for $0 with GitHub Pages
1. Create a free account at https://github.com/ (a brand account may still require private legal details with service providers).
2. Click **+** > **New repository**. Name it `bidscout`, choose **Public**, then click **Create repository**.
3. In the new repository, choose **Add file** > **Upload files**.
4. Upload **index.html**, **styles.css**, and **app.js** from the `bidscout` folder. (Do not upload the ZIP alone.) Click **Commit changes**.
5. Open repository **Settings** > **Pages**.
6. Under **Build and deployment**, choose **Deploy from a branch**. Select `main` and `/ (root)` and click **Save**.
7. Wait a few minutes, then visit `https://YOUR-USERNAME.github.io/bidscout/` (replace YOUR-USERNAME with your actual GitHub username). GitHub Pages will also show the live URL in Settings > Pages.
8. Test search, category, state filters, and saved items on your phone.

GitHub's menus may change slightly. GitHub Pages publishes static content publicly; do not put passwords or secrets in these files. A free github.io URL does not require buying a domain.

## Updating demo data
Edit `opportunities` at the top of `app.js`. For real bids, add verified source URLs, source/verification timestamps, and a prominent link to the official issuing agency. Never publish fabricated bid values, dates, or match scores as factual data.

## Next production steps
1. Verify the real market demand and interview contractors.
2. Research official state/local procurement sources and their reuse rules.
3. Add verified bid entries with source links, deadlines, and last-checked dates.
4. Add an update workflow; remove expired opportunities.
5. Only then consider alerts, accounts, or subscriptions. Static GitHub Pages does not provide server-side authentication or scheduled data ingestion by itself.
