#pragma once 

#include "Wire.h"

class IR {
    private:

    public:
        void I2C_connect(void);
        void start_up(void);    
        int read_stat();
        byte read_power();
};
