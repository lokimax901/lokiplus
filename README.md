# LokiPlus

A client management system built with Flask and Supabase.

## Features

- Client Management
  - Add, edit, and delete clients
  - Track client renewal dates
  - Automatic next renewal date calculation
  - Client-account linking system
- Account Management
  - Secure account creation and management
  - Status tracking (active/inactive)
  - Client association (up to 5 clients per account)
- Health Monitoring
  - Real-time database health checks
  - Route performance monitoring
  - System status dashboard
- Database Health Checking
  - Automatic connection validation
  - Performance metrics
  - Error tracking and reporting

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python)
- Database: Supabase (PostgreSQL)

## Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/lokimax901/lokiplus.git
   cd lokiplus
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Unix/MacOS
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   FLASK_ENV=development
   FLASK_DEBUG=1
   ```

5. Run the application:
   ```bash
   python src/app.py
   ```

## Deployment

### Frontend (Netlify)
The frontend is deployed on Netlify. Visit [https://lokiplus.netlify.app](https://lokiplus.netlify.app) to access the application.

### Backend (Render)
The backend API is deployed on Render. The API endpoint is:
```
https://lokiplus-api.onrender.com
```

### Environment Variables
Make sure to set the following environment variables in your deployment platform:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase project API key
- `FLASK_ENV`: Set to "production"
- `FLASK_DEBUG`: Set to "0"

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 