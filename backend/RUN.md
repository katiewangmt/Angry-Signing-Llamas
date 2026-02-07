# How to run the backend

You need **Java 17** installed. You don't need to install Maven (the project has a wrapper).

## 0. Install Java 17 (one-time)

If you see "Unable to locate a Java Runtime" or "BUILD FAILURE ... exit code: 1", install Java:

**Mac (Homebrew):**
```bash
brew install openjdk@17
```

Then add it to your PATH (add to `~/.zshrc` or run once in the terminal):
```bash
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"
```
(On Intel Mac it might be `/usr/local/opt/openjdk@17/bin`.)

**Or** download the JDK 17 installer from [Adoptium](https://adoptium.net/) or [Oracle](https://www.oracle.com/java/technologies/downloads/#java17) and install it.

**Check:** Run `java -version`. You should see something like "openjdk version 17.x.x".

---

## 1. Go to the backend folder

```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
```

(If you're already in the project root and see `backend-java`, you can use `cd backend-java`.)

## 2. Start the app

```bash
./mvnw spring-boot:run
```

The first time you run this, the script will download Maven (once) into `.mvn/cache`. After that it starts quickly.

Wait until you see something like "Started Application". Then open in your browser:

**http://localhost:5000**

---

## Short version

```bash
cd /Users/wenningcikeshangan/cs_/ADI2026/backend-java
./mvnw spring-boot:run
```

Then open **http://localhost:5000**. No `brew install maven` needed.
