#include <iostream>
#include <string>
#include <vector>

inline std::vector<int> _py_range(int x) {
    int i = 0;
    std::vector<int> result;
    for (size_t i = 0; i < x; i++) {
        result.push_back(i);
    }
    return result;
}

inline void int_py_print(int x){
    std::cout << x << std::endl;
}

inline void str_py_print(std::string x){
    std::cout << x << std::endl;
}

inline void float_py_print(float x){
    std::cout << x << std::endl;
}

template<typename T>
void list_py_print(std::vector<T> x){
    std::cout << "[";
    for (size_t i = 0; i < x.size(); i++) {
        std::cout << x[i];
        if (i != x.size()-1)
            std::cout << ", ";
    }
    std::cout << "]" << std::endl;
}

template<typename T>
inline int list_py_len(std::vector<T> x) {
    return x.size();
}

inline int str_py_len(std::string x) {
    return x.size();
}