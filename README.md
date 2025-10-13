# TavernAI
A lightweight, local network tavern ordering app with three frontends and a small FastAPI backend:

Waiter UI — create / edit table orders, set table meta (people, bread), finalize table

Kitchen UI — see kitchen items (non-grill), confirm items as done

Grill UI — see grill items, confirm items as done

Backend (FastAPI) — stores orders in-memory (MVP), exposes REST + WebSocket endpoints, simple NLP to classify lines into grill / kitchen / drinks

## The problem

In many traditional Greek taverns — especially in rural areas — the ordering process is still completely manual. Waiters take orders on paper, bring them to the kitchen or grill, and later re-enter each item into the cashier’s machine to print the receipt.

This manual workflow causes several issues:

Time delays: Waiters spend valuable time walking between stations and rewriting orders.

Miscommunication: Handwritten notes can be unclear or lost, leading to mistakes in the kitchen or grill.

Inefficiency: During busy hours, staff are forced to juggle multiple papers and remember which table ordered what.

No live tracking: There’s no way to see which dishes are ready without physically checking each workstation.

The result is slower service, more errors, and unnecessary stress for both the staff and customers.

## The solution

TavernAI replaces the traditional pen-and-paper workflow with a smart, connected, and AI-assisted ordering system that runs entirely on a local network, without requiring internet access.

When a waiter takes an order, they simply type it on a tablet or phone. The system’s Greek-capable NLP model automatically recognizes and classifies each dish into the correct workstation — kitchen, grill, or drinks — based on the menu.

Each workstation has its own dedicated interface:

Kitchen UI: Displays only the dishes prepared in the kitchen.

Grill UI: Displays grill items separately, with live updates.

Drinks UI: (in development) will handle beverages and bar items.

As soon as the order is sent, all relevant stations receive the items instantly through WebSockets. When a dish is prepared, the staff marks it as “done,” and the waiter sees the live status at their station.

When the table is finalized, TavernAI automatically calculates the total cost using the prices defined in menu.json, allowing the receipt to be printed or recorded immediately — no manual copying, no communication delays, and no double work.

In short, TavernAI turns a traditional taverna's chaotic, paper-based workflow into a real-time, efficient, and fully connected system. It preserves the simplicity of a traditional setting while introducing the power of modern AI and automation.
