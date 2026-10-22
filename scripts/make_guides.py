"""Build the Team RBR DM lead-magnet PDFs (A4, one page each)."""
import asyncio, base64, html, os
from playwright.async_api import async_playwright
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = os.environ.get("RBR_FONT_DIR", "/tmp/rbrfonts/node_modules/@fontsource/montserrat/files")
def b64(p, m): return f"data:{m};base64," + base64.b64encode(open(p, "rb").read()).decode()
FONTS = "".join(f"@font-face{{font-family:M;src:url({b64(f'{F}/montserrat-latin-{w}-normal.woff2','font/woff2')});font-weight:{w}}}" for w in (400,700,800))
LOGO = b64(os.path.join(REPO, "brand", "kw-eden-logo.png"), "image/png")
CSS = FONTS + """
@page{size:A4;margin:0} *{box-sizing:border-box;margin:0}
body{font-family:M;color:#2B2B2B;width:210mm;height:297mm;position:relative}
.top{background:#2B2B2B;color:#fff;padding:14mm 16mm 10mm;border-top:3mm solid #B40101}
.kick{color:#ff6b6b;font-weight:800;font-size:9pt;letter-spacing:2pt;text-transform:uppercase}
h1{font-weight:800;font-size:24pt;line-height:1.1;margin-top:3mm} .sub{font-size:10.5pt;margin-top:3mm;color:#ddd}
.main{padding:8mm 16mm 0} h2{font-size:11.5pt;font-weight:800;color:#B40101;margin:5mm 0 2mm;text-transform:uppercase;letter-spacing:.5pt}
.item{display:flex;gap:3mm;font-size:9.6pt;line-height:1.38;margin:1.6mm 0} .box{flex:0 0 4mm;height:4mm;border:.45mm solid #2B2B2B;margin-top:.6mm}
.item b{font-weight:700} .if{color:#666;font-size:8.8pt}
.cta{margin:6mm 16mm 0;background:#B40101;color:#fff;padding:5mm 7mm;font-size:10.5pt;line-height:1.4} .cta b{font-weight:800}
.note{margin:3mm 16mm 0;font-size:7.6pt;color:#777;line-height:1.35}
.foot{position:absolute;bottom:0;left:0;right:0;height:26mm;border-top:.4mm solid #ddd;display:flex;align-items:center;justify-content:space-between;padding:0 16mm;font-size:9pt;font-weight:700;line-height:1.5}
.foot img{height:14mm}
"""
def page(kick, title, sub, sections, cta, note):
    sec = ""
    for head, items in sections:
        sec += f"<h2>{html.escape(head)}</h2>"
        for t, d, f in items:
            iff = f" <span class=if>If not: {html.escape(f)}</span>" if f else ""
            sec += f"<div class=item><div class=box></div><div><b>{html.escape(t)}</b> {html.escape(d)}{iff}</div></div>"
    return (f"<html><head><meta charset=utf-8><style>{CSS}</style></head><body>"
            f"<div class=top><div class=kick>{kick}</div><h1>{html.escape(title)}</h1><div class=sub>{html.escape(sub)}</div></div>"
            f"<div class=main>{sec}</div><div class=cta>{cta}</div><div class=note>{html.escape(note)}</div>"
            f"<div class=foot><div>Ryan Butler · Team RBR<br>083 281 7918 · ryan.butler@kwsa.co.za</div><img src='{LOGO}'></div></body></html>")

GUIDES = {
"buyer-viewing-checklist": page("Free buyer guide · Team RBR", "The Viewing Checklist",
 "Take this to every viewing in George. Tick as you go, and write down anything that fails so you can ask about it before you make an offer.",
 [("Outside", [
   ("Roof and gutters.", "Look for sagging, rust, missing tiles and gutters pulling away.", "ask when the roof was last repaired and get a roof inspection quote."),
   ("Walls and boundary.", "Check for big cracks, damp patches at the base of walls, and the state of the boundary wall or fence.", "ask the seller about it and note it for your offer."),
   ("Drainage.", "Look at where water runs when it rains. Puddling against the house is a warning sign.", "ask whether the property has had water problems.")]),
  ("Inside", [
   ("Open every tap and flush every toilet.", "Check the pressure and how fast the water drains.", "low pressure or slow drains can mean plumbing work."),
   ("Look up.", "Stains or bubbling paint on ceilings and cornices can point to roof leaks.", "ask what caused it and whether it was fixed."),
   ("Switch on lights and test plugs.", "Ask whether the electrical compliance certificate is current.", "ask the seller to confirm who will arrange it."),
   ("Open windows and doors.", "Sticking doors and windows can be a sign of movement.", "note it and ask.")]),
  ("Paperwork and questions", [
   ("Ask what stays.", "Curtains, light fittings, the pool pump, the alarm system. Get it in writing in the offer.", ""),
   ("Ask about monthly costs.", "Rates, levies (if it is in an estate or complex) and any special levies.", "ask for the latest statements before you sign."),
   ("Ask why the seller is moving and how long it has been on the market.", "It helps you understand the seller's position.", "")])],
 "<b>Found a house you like?</b> Send me a message and I will help you check the comparable sales in that street before you make your offer. WhatsApp or call Ryan on 083 281 7918.",
 "This checklist is a general guide and does not replace a professional property inspection."),
"buying-costs-guide": page("Free buyer guide · Team RBR", "Buying in George: the costs on top of the price",
 "The purchase price is only part of what you will pay. Use this list to plan your budget with your bank and your conveyancing attorney before you make an offer.",
 [("Once-off costs", [
   ("Deposit.", "Many buyers need some deposit, depending on the bank's approval.", "speak to a bond originator early so you know your number."),
   ("Transfer costs.", "The conveyancing attorney's fees, plus transfer duty if the price is above the exemption threshold.", "ask the attorney for a written cost estimate."),
   ("Bond registration costs.", "A separate attorney bill if you are taking a home loan.", "ask for this estimate at the same time."),
   ("Bank initiation fee.", "Most banks charge this when the home loan is approved.", "check whether it can be added to the loan."),
   ("Moving costs and small fixes.", "Movers, connecting utilities, and the small jobs every new home needs.", "")]),
  ("Monthly costs", [
   ("Bond repayment.", "Based on your loan amount, interest rate and term.", "ask your bank for the exact repayment."),
   ("Rates and taxes.", "Charged by George Municipality.", "ask the seller for the latest rates account."),
   ("Levies.", "Only if the property is in an estate or sectional title scheme.", "ask for the levy statement and any special levies."),
   ("Insurance.", "Building insurance (often required by the bank) and household contents cover.", "get quotes before transfer.")])],
 "<b>Want a cost breakdown for a specific home?</b> Send me the listing and I will help you work through it with a conveyancer. WhatsApp or call Ryan on 083 281 7918.",
 "This guide is general information only. Your attorney and bank will give you the exact amounts for your purchase."),
"seller-prep-checklist": page("Free seller guide · Team RBR", "Get your home ready to sell",
 "Small jobs before you list help buyers fall in love with your home. Work through this list, then book your free market analysis to find out where your price should be.",
 [("Fix", [
   ("Leaking taps, cracked tiles and sticking doors.", "Buyers notice small faults and assume there are bigger ones.", "fix them or get a quote to show buyers."),
   ("Blown bulbs and broken fittings.", "Every light should work on viewing day.", ""),
   ("Paperwork.", "Find your plans, rates account, levy statements and any guarantees.", "we can help you request copies.")]),
  ("Clean and declutter", [
   ("Clear surfaces and pack away personal items.", "Buyers need to picture their own things in the space.", ""),
   ("Deep-clean kitchens and bathrooms.", "These rooms sell homes.", ""),
   ("Tidy the garden and entrance.", "First impressions start at the gate.", "")]),
  ("Light and space", [
   ("Open curtains and clean windows.", "Bright rooms look bigger in photos and in person.", ""),
   ("Move out extra furniture.", "Fewer pieces make rooms feel larger.", "")])],
 "<b>Ready to find out what your home could sell for?</b> Book a free, no-obligation market analysis. I compare your home with recent sales and homes on the market around you. WhatsApp or call Ryan on 083 281 7918.",
 "Team RBR, Keller Williams Eden. Market analyses are free and carry no obligation to list."),
}
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page()
        for name, doc in GUIDES.items():
            await pg.set_content(doc); await pg.evaluate("document.fonts.ready")
            await pg.pdf(path=os.path.join(REPO, "guides", f"{name}.pdf"), format="A4", print_background=True)
            await pg.screenshot(path=f"/tmp/{name}.png", full_page=True)
            print(name)
        await b.close()
asyncio.run(main())
