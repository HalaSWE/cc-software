**CC Software: Cost Control System**
**Jouf University | College of Computer and Information Sciences** **Team:** Welaf Alshaya, Hajar Almudhyan, Renad Alnussairy, Hala Alruwaili  
**Supervisor:** Dr. Al Assaad Mejri

---

## **What is this project?**
We created **CC Software** to solve a common problem: organizations relying on messy Excel sheets to track projects. Our web-based system provides a clear, real-time view of performance by automatically calculating financial metrics like **ROI, NPV, and EVM**, helping managers decide which projects are actually worth the investment.

---

## **The Team**
This was a true collaborative effort. We divided the work between backend logic, frontend UI, database architecture, and testing, ensuring every feature was peer-reviewed before completion.

---

## **What the system can do**

### **Managing Projects**
Easily set up projects with budgets and timelines. The system uses secure access control, so team members only see the projects they are assigned to.

### **Work Breakdown Structure (WBS)**
Each project is broken into tasks. You simply input the planned value, actual cost, and percentage complete—the system handles all the complex math from there.

### **Earned Value Management (EVM)**
The core of our system. It automatically updates **10 key metrics** (like CPI, SPI, and EAC) every time a task changes, showing exactly if you are over budget or behind schedule.

### **Project Selection and Scoring**
When choosing between multiple proposals, the system scores them out of **100 points** based on financial health (ROI, BCR, Payback, and NPV) to help managers make data-driven decisions.

### **Analytics**
A high-level dashboard provides a portfolio view, identifying "at-risk" projects and assigning risk levels from **Low to Critical** based on performance trends.

### **Reports and Exports**
Need to share data? You can generate comprehensive **PDF reports** or export raw data to **CSV** files in seconds.

### **Notifications**
Stay in the loop with real-time alerts for new tasks, new team members, or project updates.

### **User Profiles**
Users have dedicated pages to manage their identity, update bios, and track their project enrollments.

---

## **User Roles**
To keep data secure, we implemented three distinct access levels:

| Feature | Member | Manager | Admin |
| :--- | :---: | :---: | :---: |
| Update tasks & comments | Yes | Yes | Yes |
| Manage projects & teams | No | Yes | Yes |
| Enter financial/scoring data | No | Yes | Yes |
| System-wide admin & users | No | No | Yes |

---

## **Technology Stack**
We chose a **"Vanilla" approach** for the frontend to keep the system fast and easy to run without complex build tools.

* **Backend:** Python (FastAPI) & SQLAlchemy
* **Database:** PostgreSQL (Supabase)
* **Frontend:** Pure HTML5, CSS3, & JavaScript (Chart.js for visuals)
* **Security:** JWT Tokens & Bcrypt hashing

---

## **Project Structure**
The project is organized into a clean **Backend/Frontend** split. The backend handles logic via modular routes (Auth, Analytics, Reports), while the frontend remains lightweight in a single-page style.

---

## **How to Run It**

### **Backend**
1. Install dependencies: `pip install -r requirements.txt`
2. Create a `.env` file with your `DATABASE_URL` and `SECRET_KEY`.
3. Run: `uvicorn main:app --reload`

### **Frontend**
Simply open `frontend/index.html` in any modern browser. (Ensure the `API` constant in `app.js` matches your backend URL).

### **API Docs**
Access interactive documentation at: `http://localhost:8000/docs`

---

## **Default Admin Account**
* **Username:** admin
* **Password:** Admin@1234

---

## **A Note from the Team**
This project represents months of hard work, from database refactoring to UI polishing. We are incredibly proud of the result and hope it serves as a helpful reference for future students!

– Welaf, Hajar, Renad, and Hala :)