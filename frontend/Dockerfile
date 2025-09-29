# Stage 1: Build the React app
FROM node:20-alpine as build
WORKDIR /app
COPY package.json vite.config.js tailwind.config.js postcss.config.js index.html ./
COPY src ./src
COPY public ./public
RUN npm install && npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# React router + API proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]