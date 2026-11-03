#ifndef INCLUDED_VECTOR_H
#define INCLUDED_VECTOR_H

#include <cassert>
#include <cstddef>
#include <new>
#include <utility>

template <typename T> class Vector {

public:
  Vector() noexcept = default;

  explicit Vector(std::size_t n) {

    if (n > 0) {
      capacity_ = n;
      // alloate mem based on T size
      void *raw = ::operator new(n * sizeof(T));
      data_ = static_cast<T *>(raw);

      try {
        // construct element
        for (std::size_t i = 0; i < n; i++) {
          ::new (static_cast<void *>(data_ + i)) T{};
          ++size_;
        }
      } catch (...) {
        for (std::size_t i = 0; i < size_; i++) {
          data_[i].~T();
        }
        ::operator delete(data_);
        throw;
      }
    }
  }

  ~Vector() {
    for (size_t i = 0; i < size_; ++i) {
      data_[i].~T();
    }
    // free storage
    ::operator delete(data_);
  };

  Vector(const Vector &other) {
    capacity_ = other.capacity_;

    data_ = static_cast<T *>(::operator new(capacity_ * sizeof(T)));

    try {
      for (std::size_t i = 0; i < other.size_; i++) {
        ::new (static_cast<void *>(data_ + i)) T(other[i]);
        ++size_;
      }
    } catch (...) {
      for (std::size_t i = 0; i < size_; i++) {
        data_[i].~T();
      }
      ::operator delete(data_);
      throw;
    }
  }
  Vector &operator=(const Vector &other) {

    Vector temp(other); // so we preserve othe r just in case
    std::swap(data_, temp.data_);
    std::swap(size_, temp.size_);
    std::swap(capacity_, temp.capacity_);

    return *this;
  }

  Vector &operator=(Vector &&other) noexcept { // move assign

    Vector temp(std::move(other));

    std::swap(data_, temp.data_);
    std::swap(size_, temp.size_);
    std::swap(capacity_, temp.capacity_);

    return *this;
  }

  Vector(Vector &&other) noexcept { // move ctor

    data_ = std::move(other.data_);
    size_ = other.size_;
    capacity_ = other.capacity_;

    other.data_ = nullptr;
    other.size_ = 0;
    other.capacity_ = 0;
  }

  void push_back(const T &value) { emplace_back(value); }
  void push_back(T &&value) { emplace_back(std::move(value)); }
  T &operator[](std::size_t index) noexcept { return data_[index]; }
  const T &operator[](std::size_t index) const noexcept { return data_[index]; }

  std::size_t size() const noexcept { return size_; }
  std::size_t capacity() const noexcept { return capacity_; }

  template <class... Args> T &emplace_back(Args &&...args) {

    if (size_ == capacity_) {
        std::size_t counter = 0;
        std::size_t new_capacity_ = capacity_ == 0 ? 1 :  capacity_ * 2;
        T *new_data =
            static_cast<T *>(::operator new(new_capacity_ * sizeof(T)));
        bool elementConstructed = false;
        try {
        // handle cases like emplace_back(values[0])

          T *member = ::new (static_cast<void *>(new_data + size_))
              T(std::forward<Args>(args)...);
          elementConstructed = true;
          for (std::size_t i = 0; i < size_; i++) {
            ::new (static_cast<void *>(new_data + i))
                T(std::move_if_noexcept(data_[i]));
            ++counter;
          }
          for (std::size_t i = 0; i < size_; i++) {
            data_[i].~T();
          }
          ++size_;
          capacity_ = new_capacity_;
          ::operator delete(data_);
          data_ = new_data;
          return *member;
        } catch (...) {
          for (std::size_t i = 0; i < counter; i++) {
            new_data[i].~T();
          }
          if (elementConstructed) {
            new_data[size_].~T();
          }
          ::operator delete(new_data);
          throw;
        }
      }
    
    T *new_member = ::new (static_cast<void *>(data_ + size_))
        T(std::forward<Args>(args)...);
    ++size_;
    return *new_member;
  }

  void reserve(std::size_t n) {
    if (n <= capacity_)
      return;
    T *new_data = static_cast<T *>(::operator new(n * sizeof(T)));

    std::size_t counter = 0;
    try {
      for (std::size_t i = 0; i < size_; i++) {
        // move rather than copyting if the move constructor does not throw
        ::new (static_cast<void *>(new_data + i))
            T(std::move_if_noexcept(data_[i]));
        ++counter;
      }
      for (std::size_t i = 0; i < size_; i++) {
        data_[i].~T();
      }
      capacity_ = n;
      ::operator delete(data_);
      data_ = new_data;
    } catch (...) {
      // desytoy thr objects in the new allocated memory
      for (std::size_t i = 0; i < counter; i++) {
        new_data[i].~T();
      }
      ::operator delete(new_data);
      throw;
    }
  }

  void pop_back() {
    assert(size_ > 0);

    data_[size_ - 1].~T();
    --size_;
  }

  void clear() {
    while (size_ > 0) {
      pop_back();
    }
  }

  T *begin() noexcept { return data_; }
  T *end() noexcept {
    if (size_ == 0)
      return data_;
    return data_ + size_;
  }

  const T *begin() const noexcept { return data_; }
  const T *end() const noexcept {
    if (size_ == 0)
      return data_;
    return data_ + size_;
  }

  
  private : T *data_ = nullptr;
  std::size_t size_ = 0;
  std::size_t capacity_ = 0;
};

#endif