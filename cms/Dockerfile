FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Provide custom nginx config if necessary for SPA routing
RUN echo "server { listen 80; location / { root /usr/share/nginx/html; index index.html; try_files \$uri \$uri/ /index.html; } location /api/ { proxy_pass http://api:8000/; } location /admin/ { proxy_pass http://api:8000/admin/; } location /auth/ { proxy_pass http://api:8000/auth/; } location /media/ { proxy_pass http://api:8000/media/; } }" > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
