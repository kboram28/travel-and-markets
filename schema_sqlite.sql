-- ============================================
-- ERDCloud 가져오기용 DDL
-- ERDCloud > SQL 가져오기(Import) > 이 전체를 붙여넣으면 테이블이 자동 생성됩니다.
-- ============================================

-- 1. 사용자 / 인증
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username VARCHAR(100),
  password_hash VARCHAR(255),
  login_type VARCHAR(20),
  name VARCHAR(50),
  birth_date DATE,
  gender VARCHAR(10),
  nationality VARCHAR(20),
  phone VARCHAR(20),
  phone_verified BOOLEAN,
  preferred_theme VARCHAR(50),
  preferred_companion VARCHAR(50),
  preferred_region VARCHAR(50),
  budget_range VARCHAR(50),
  profile_image VARCHAR(255),
  status VARCHAR(20),
  created_at DATETIME
);

CREATE TABLE social_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  provider VARCHAR(20),
  provider_user_id VARCHAR(100),
  access_token VARCHAR(255),
  refresh_token VARCHAR(255),
  connected_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE merchant_teams (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_name VARCHAR(100),
  invite_code VARCHAR(50),
  created_at DATETIME
);

CREATE TABLE merchants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username VARCHAR(100),
  password_hash VARCHAR(255),
  store_name VARCHAR(100),
  category VARCHAR(50),
  contact_phone VARCHAR(20),
  settlement_bank VARCHAR(50),
  settlement_account VARCHAR(50),
  settlement_holder VARCHAR(50),
  business_type VARCHAR(20),
  business_number VARCHAR(50),
  approval_status VARCHAR(20),
  team_id INT,
  created_at DATETIME,
  FOREIGN KEY (team_id) REFERENCES merchant_teams(id)
);

CREATE TABLE merchant_documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  merchant_id INT,
  document_type VARCHAR(50),
  file_url VARCHAR(255),
  status VARCHAR(20),
  rejection_reason TEXT,
  submitted_at DATETIME,
  FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- 2. 시장 / 매장 / 상품
CREATE TABLE markets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100),
  market_type VARCHAR(50),
  address VARCHAR(255),
  lat FLOAT,
  lng FLOAT,
  open_cycle VARCHAR(50),
  items TEXT,
  has_restroom BOOLEAN,
  has_parking BOOLEAN,
  store_count INT
);

CREATE TABLE stores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  merchant_id INT,
  market_id INT,
  name VARCHAR(100),
  location_detail VARCHAR(255),
  operating_info TEXT,
  photos TEXT,
  status VARCHAR(20),
  FOREIGN KEY (merchant_id) REFERENCES merchants(id),
  FOREIGN KEY (market_id) REFERENCES markets(id)
);

CREATE TABLE products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id INT,
  name VARCHAR(100),
  stock INT,
  price INT,
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE team_members (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  team_id INT,
  merchant_id INT,
  joined_at DATETIME,
  FOREIGN KEY (team_id) REFERENCES merchant_teams(id),
  FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

CREATE TABLE discounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id INT,
  discount_rate INT,
  target_product_id INT,
  start_date DATE,
  end_date DATE,
  FOREIGN KEY (store_id) REFERENCES stores(id),
  FOREIGN KEY (target_product_id) REFERENCES products(id)
);

CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id INT,
  content TEXT,
  participation_method TEXT,
  start_date DATE,
  end_date DATE,
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE merchant_schedules (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  merchant_id INT,
  team_id INT,
  date DATE,
  market_id INT,
  status VARCHAR(20),
  FOREIGN KEY (merchant_id) REFERENCES merchants(id),
  FOREIGN KEY (team_id) REFERENCES merchant_teams(id),
  FOREIGN KEY (market_id) REFERENCES markets(id)
);

-- admins (markets 참조 필요해서 markets 정의 뒤로 배치)
CREATE TABLE admins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username VARCHAR(100),
  password_hash VARCHAR(255),
  role VARCHAR(20),
  scope_market_id INT,
  scope_region_code VARCHAR(20),
  status VARCHAR(20),
  created_at DATETIME,
  FOREIGN KEY (scope_market_id) REFERENCES markets(id)
);

-- 3. 관광 / 여행지
CREATE TABLE attractions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content_id VARCHAR(50),
  name VARCHAR(100),
  address VARCHAR(255),
  image VARCHAR(255),
  category VARCHAR(50),
  lcls1_name VARCHAR(50),
  lcls2_name VARCHAR(50),
  lcls3_name VARCHAR(50),
  area_code VARCHAR(10),
  sigungu_name VARCHAR(50),
  lat FLOAT,
  lng FLOAT,
  tel VARCHAR(20)
);

CREATE TABLE favorites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  attraction_id INT,
  market_id INT,
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (attraction_id) REFERENCES attractions(id),
  FOREIGN KEY (market_id) REFERENCES markets(id)
);

-- 4. 예약
CREATE TABLE reservations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  store_id INT,
  pickup_time DATETIME,
  status VARCHAR(20),
  rejection_reason TEXT,
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE reservation_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reservation_id INT,
  product_id INT,
  quantity INT,
  FOREIGN KEY (reservation_id) REFERENCES reservations(id),
  FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 5. 챗봇 / 일정
CREATE TABLE chatbot_conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  title VARCHAR(100),
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE chatbot_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INT,
  sender VARCHAR(10),
  content TEXT,
  created_at DATETIME,
  FOREIGN KEY (conversation_id) REFERENCES chatbot_conversations(id)
);

CREATE TABLE itineraries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  conversation_id INT,
  title VARCHAR(100),
  start_date DATE,
  end_date DATE,
  theme VARCHAR(50),
  companion_type VARCHAR(50),
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (conversation_id) REFERENCES chatbot_conversations(id)
);

CREATE TABLE itinerary_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  itinerary_id INT,
  day_number INT,
  attraction_id INT,
  market_id INT,
  visit_order INT,
  FOREIGN KEY (itinerary_id) REFERENCES itineraries(id),
  FOREIGN KEY (attraction_id) REFERENCES attractions(id),
  FOREIGN KEY (market_id) REFERENCES markets(id)
);

CREATE TABLE itinerary_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  itinerary_id INT,
  satisfaction VARCHAR(20),
  comment TEXT,
  created_at DATETIME,
  FOREIGN KEY (itinerary_id) REFERENCES itineraries(id)
);

-- 6. 리뷰 / QR / 쿠폰
CREATE TABLE reviews (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  store_id INT,
  rating INT,
  content TEXT,
  photo VARCHAR(255),
  status VARCHAR(20),
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE review_analysis (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  store_id INT,
  good_points TEXT,
  improvement_points TEXT,
  analyzed_at DATETIME,
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE review_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  review_id INT,
  reporter_user_id INT,
  reason VARCHAR(100),
  status VARCHAR(20),
  created_at DATETIME,
  FOREIGN KEY (review_id) REFERENCES reviews(id),
  FOREIGN KEY (reporter_user_id) REFERENCES users(id)
);

CREATE TABLE qr_checkins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  store_id INT,
  checked_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (store_id) REFERENCES stores(id)
);

CREATE TABLE stamps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  market_id INT,
  stamp_count INT,
  updated_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (market_id) REFERENCES markets(id)
);

CREATE TABLE coupon_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INT,
  title VARCHAR(100),
  discount_content VARCHAR(255),
  valid_days INT,
  created_at DATETIME,
  FOREIGN KEY (admin_id) REFERENCES admins(id)
);

CREATE TABLE coupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  coupon_template_id INT,
  issued_at DATETIME,
  expires_at DATETIME,
  status VARCHAR(20),
  used_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (coupon_template_id) REFERENCES coupon_templates(id)
);

-- 7. 정산 / 매출
CREATE TABLE settlements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  merchant_id INT,
  period_start DATE,
  period_end DATE,
  total_sales INT,
  fee INT,
  settlement_amount INT,
  status VARCHAR(20),
  settled_at DATETIME,
  FOREIGN KEY (merchant_id) REFERENCES merchants(id)
);

-- 8. 알림 / 고객센터
CREATE TABLE notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  type VARCHAR(30),
  content TEXT,
  is_read BOOLEAN,
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE notification_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  all_notifications BOOLEAN,
  reservation_alert BOOLEAN,
  review_reply_alert BOOLEAN,
  event_alert BOOLEAN,
  stamp_coupon_alert BOOLEAN,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE notices (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  admin_id INT,
  title VARCHAR(100),
  content TEXT,
  expires_at DATE,
  created_at DATETIME,
  FOREIGN KEY (admin_id) REFERENCES admins(id)
);

CREATE TABLE faqs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category VARCHAR(50),
  question TEXT,
  answer TEXT
);

CREATE TABLE inquiries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INT,
  type VARCHAR(30),
  content TEXT,
  status VARCHAR(20),
  answer TEXT,
  created_at DATETIME,
  FOREIGN KEY (user_id) REFERENCES users(id)
);