"""Seed placeholder menu items if the menu is empty. Real items/photos replace these later
(swap photo_path to the uploaded image and edit names/prices)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MenuItem

# (name, blurb, price_cents, photo_path, sort). Prices are easy to tweak here.
PLACEHOLDERS = [
    ("Grilled Cheese", "The legendary night-market grilled cheese. The one you came for.", 800, "/media/grilledcheese.jpg", 1),
    ("Smash Burger", "Double patty, melty cheese, zero regrets.", 1200, "/media/burger.jpg", 2),
    ("Loaded Nachos", "A mountain of chips under everything we had.", 1000, "/media/nachos.jpg", 3),
    ("Corn Dog", "Golden, crispy, on a stick. As nature intended.", 600, "/media/corndog.jpg", 4),
    ("Pancakes", "A short stack for breakfast-anytime energy.", 700, "/media/pancake.jpg", 5),
    ("Hash Browns", "Crispy potato perfection.", 500, "/media/hashbrown.jpeg", 6),
    ("Slushie", "Ice-cold, electric-blue, mildly irresponsible.", 400, "/media/slushie.jpeg", 7),
]


async def seed_menu_if_empty(db: AsyncSession) -> None:
    count = (await db.execute(select(func.count()).select_from(MenuItem))).scalar_one()
    if count:
        return
    for name, blurb, price, photo, sort in PLACEHOLDERS:
        db.add(MenuItem(name=name, blurb=blurb, price_cents=price, photo_path=photo, sort=sort))
    await db.commit()
