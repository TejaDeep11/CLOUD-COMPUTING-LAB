from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import get_db
from checkout import checkout_logic

app = FastAPI()
SRN = "PES2UG23CS135"
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup():
    db = get_db()
    db.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, fee INTEGER)")
    db.execute("CREATE TABLE IF NOT EXISTS registrations (username TEXT, event_id INTEGER)")
    
    # Insert sample events if table is empty
    count = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    if count == 0:
        events = [
            ("Hackathon", 500),
            ("Dance Battle", 300),
            ("AI Workshop", 400),
            ("Photography Walk", 200),
            ("Gaming Tournament", 350),
            ("Music Night", 250),
            ("Treasure Hunt", 150),
            ("Stand-up Comedy", 300),
            ("Robo Race", 450),
        ]
        for e in events:
            db.execute("INSERT INTO events (name, fee) VALUES (?, ?)", e)
    
    db.commit()


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    db = get_db()
    try:
        db.execute("INSERT INTO users VALUES (?,?)", (username, password))
        db.commit()
    except:
        return HTMLResponse("Username already exists. Try a different one.")
    return RedirectResponse("/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()

    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "❌ Invalid username or password", "user": ""}
        )

    return RedirectResponse(f"/events?user={username}", status_code=302)



@app.get("/events", response_class=HTMLResponse)
def events(request: Request, user: str):
    db = get_db()
    rows = db.execute("SELECT * FROM events").fetchall()

    # waste = 0
    # for i in range(500000):
    #     waste += i % 3

    return templates.TemplateResponse(
        "events.html",
        {"request": request, "events": rows, "user": user}
    )


@app.get("/register_event/{event_id}")
def register_event(event_id: int, user: str):
    db = get_db()
    db.execute("INSERT INTO registrations VALUES (?,?)", (user, event_id))
    db.commit()

    return RedirectResponse(f"/my-events?user={user}", status_code=302)


@app.get("/my-events", response_class=HTMLResponse)
def my_events(request: Request, user: str):
    db = get_db()
    rows = db.execute(
        """
        SELECT events.name, events.fee
        FROM events
        JOIN registrations ON events.id = registrations.event_id
        WHERE registrations.username=?
        """,
        (user,)
    ).fetchall()



    return templates.TemplateResponse(
        "my_events.html",
        {"request": request, "events": rows, "user": user}
    )


@app.get("/checkout", response_class=HTMLResponse)
def checkout(request: Request):
    total = checkout_logic()
    return templates.TemplateResponse(
        "checkout.html",
        {"request": request, "total": total, "user": ""}
    )

@app.post("/checkout", response_class=HTMLResponse)
def checkout_post(request: Request, srn: str = Form(...)):
    total = checkout_logic()
    # Process payment with SRN
    return templates.TemplateResponse(
        "checkout.html",
        {"request": request, "total": total, "user": srn, "success": True}
    )
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Try to keep user on UI even when it crashes
    user = request.query_params.get("user", "")

    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "status_code": 500,
            "detail": str(exc),
            "user": user
        },
        status_code=500
    )