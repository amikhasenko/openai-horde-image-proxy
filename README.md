# OpenAI Horde image proxy App

OpenAI API compatible image generation proxy to AI Horde

[Open AI API](https://platform.openai.com/docs/api-reference/images/create) -> [AI Horde API](https://aihorde.net/api)

## Requirements

- Docker

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/amikhasenko/openai-horde-image-proxy/
cd openai-horde-image-proxy
```

### 2. Build and Start the Application

Use Docker Compose to build and start the application:

```bash
docker-compose up --build
```

This command will:
- Build the Docker image from the `Dockerfile`.
- Start the Flask app in a container named `my-flask-container`.

Alternativly
```
sudo docker build -t openai-horde-image-proxy .
docker run -p 5000:5000 --name openai-horde-image-proxy openai-horde-image-proxy
```

### 3. Access the Application

Served endpoint:
```
http://localhost:5000/v1/images/generations
```

### 4. API Key (optional) and model

API key provided with the request. You can get it [here](https://aihorde.net/register)

Using anonimosly also posible with key `0000000000`

### 5. Docker Compose Configuration

The `docker-compose.yml` file configures the application to:
- Build the Docker image from the current directory.
- Set the container name to `my-flask-container`.
- Expose port `5000`.

## Gunicorn Configuration

The app uses **Gunicorn** as the WSGI server for production. Gunicorn is configured to use multiple workers, based on the CPU count, to efficiently handle incoming requests.
workers = cores // 2 + 1

## Stopping the Application

To stop the application and remove the container, use:

```bash
docker-compose down
```

## Logging

You can view the logs of the running container in real time with:

```bash
docker logs -f my-flask-container
```

## Notes

- The app is designed to be lightweight and handle requests to the AI Horde API securely.
- Ensure that your API key is kept secure and not hardcoded directly in the code.

## Contributing

We welcome contributions to improve this project! To contribute:

1. Fork the repository.
2. Create a new branch for your changes (`git checkout -b feature-name`).
3. Make your changes and commit them (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-name`).
5. Create a new pull request.

## License

This project is licensed under the MIT License.

## TODO

- [ ] Add proper error handling for AI Horde API rate limits.
- [ ] Optimize image generation request parameters for better performance.
- [ ] Improve logging with more granular levels (e.g., `INFO`, `DEBUG`, `WARNING`).
- [ ] Implement user authentication for API access.

Support more endpoints:
- [ ] Text generation
- [ ] Img2img
