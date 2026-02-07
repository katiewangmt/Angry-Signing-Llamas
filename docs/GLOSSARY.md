# CORS, Vue, and Maven — short explanations

## CORS (Cross-Origin Resource Sharing)

**What it is:** A browser security rule. When a page at **origin A** (e.g. `http://localhost:3000`) uses JavaScript to request a URL at **origin B** (e.g. `http://localhost:5000`), the browser says: “Different origin — I’ll block this unless B explicitly allows A.”

**Origin** = scheme + host + port. So `http://localhost:3000` and `http://localhost:5000` are different origins.

**Why it exists:** So random websites can’t use your browser to call your bank or your APIs without the server agreeing.

**What we did:** The Java backend sends headers that say “requests from `http://localhost:3000` are allowed.” So a frontend on port 3000 can call `http://localhost:5000/api/random-music` without the browser blocking it.

**In one sentence:** CORS is the browser’s “same-origin” rule; the server can allow other origins (like your frontend) by sending CORS headers.

---

## Vue

**What it is:** A JavaScript **framework** for building UIs. You write components (HTML + JS + CSS together), and Vue handles updating the page when data changes (reactive data binding).

**Typical use:** Single-page apps (SPA): buttons, forms, lists that update without full page reloads. You’d use Vue (or React, Svelte, etc.) when the frontend gets complex.

**For this project:** You don’t need Vue to test the backend. A plain HTML + JavaScript page is enough. Vue would be useful if you later build a bigger, more interactive ASL freestyle app.

**In one sentence:** Vue is a frontend framework for building reactive UIs; we’re not using it for the simple test page.

---

## Maven

**What it is:** A **build tool** for Java. It:

- **Downloads dependencies** (e.g. Spring Boot) from the internet and puts them in a local cache.
- **Compiles** your `.java` files.
- **Runs** your app (e.g. `mvn spring-boot:run`).
- **Packages** the app (e.g. into a JAR) for deployment.

**You use it via:** The `pom.xml` file (project config + list of dependencies) and commands like `mvn compile`, `mvn spring-boot:run`, `mvn package`.

**In one sentence:** Maven is the build and dependency manager for this Java backend; you run the app with `mvn spring-boot:run`.
