from flask import Flask, render_template_string
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    # Allow cross-origin requests from anywhere.
    CORS(app)

    # Import and register the analytics blueprint.
    from blueprints.analytics_service import analytics_service

    app.register_blueprint(analytics_service, url_prefix="/analytics")

    @app.route("/")
    def index():
        html = """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8">
            <title>Flask Application Running</title>
            <style>
              body { font-family: Arial, sans-serif; background: #f0f0f0; margin: 0; padding: 20px; }
              .container { max-width: 600px; margin: auto; text-align: center; padding: 50px; background: #fff; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
              h1 { color: #333; }
            </style>
          </head>
          <body>
            <div class="container">
              <h1>Flask Application is Running!</h1>
              <p>Welcome to your Flask Application.</p>
            </div>
          </body>
        </html>
        """
        return render_template_string(html)

    return app


if __name__ == "__main__":
    app = create_app()
    # Host "0.0.0.0" allows traffic from any network interface.
    app.run(host="0.0.0.0", port=6000, debug=True)
