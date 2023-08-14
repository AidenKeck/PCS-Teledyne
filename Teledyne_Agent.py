from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE
import time
from ocs import ocs_agent, site_config
from ocs.ocs_twisted import TimeoutLock
import argparse

class Teledyne:
    '''
    Class to control and retrieve data form the teledyne HVG-2020B

    Args:
        port (fixed for this device)

    Attributes:
        read_pressure reads current pressure from gauge
        close closes the connection between computer and arduino

    '''
    def __init__(self, port, baud = 19200, timeout = 0.1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.connection = Serial(self.port, baudrate=self.baud, bytesize=EIGHTBITS, parity=PARITY_NONE, stopbits=STOPBITS_ONE, timeout=None,xonxoff=False, rtscts=False)
    
    def read_pressure(self):
        """
        Sends command to teledyne gauge so it can begin acquiring pressure. 
        """
        self.connection.write('p\r\n'.encode("utf-8"))
        time.sleep(0.1)
        
        #Keeps reading information from teledyne until information being sent has completed (signified by receiving ' ')
        read = []
        while True:
            text = self.connection.readline(1)
            decode = text.decode("utf-8")
            read.append(decode)
            if text.decode("utf-8") == ' ':
                break
        
        #Transforms data gathred into a usable float
        currentPressure = float(''.join(map(str, read)).replace('\r>', ''))
        return currentPressure
    
    
    def close(self):
        """
        Closes connection with Teledyne Pressure gauge.
        """
        self.connection.close()


class Teledyne_Agent:

    def __init__(self, agent, port, f_sample=2.5):
        self.active = True
        self.agent: ocs_agent.OCSAgent = agent
        self.log = agent.log
        self.lock = TimeoutLock()
        self.port = port
        self.f_sample = f_sample
        self.take_data = False
        self.gauge = Teledyne(port)
        agg_params = {'frame_length': 60, }
        self.agent.register_feed('pressure',
                                 record=True,
                                 agg_params=agg_params,
                                 buffer_time=1)
    
    #Enables client to acquire pressure data from Teledyne pressure gauge
    @ocs_agent.param('sampling_frequency', type=float, default = 2.5)
    @ocs_agent.param('test_mode', type = bool, default = False)
    def acq(self, session, params=None):
        #Determining how many times per second to sample data, defaults to 2.5 times per second
        if params is None:
            params = {}
        f_sample = params['sampling_frequency']
        if f_sample is None:
            f_sample = self.f_sample

        sleep_time = 1. / f_sample - 0.01
        
        #Ensures that multiple clients do not try to use function at same time
        with self.lock.acquire_timeout(timeout=0, job='init') as acquired:
            if not acquired:
                self.log.warn("Could not start init because {} is already running".format(self.lock.job))
                return False, "Could not acquire lock."
            
            session.set_status('running')

            self.take_data = True
            
            session.data = {'fields': {}}
            
            #Creates data object, sampling pressure and related timestamp that can be used for automation script and Grafana display
            while self.take_data:
                current_time = time.time()
                data = {
                    'timestamp': current_time,
                    'block_name':  'pressure',
                    'data': {}
                }
                pressure_line = self.gauge.read_pressure()
                data['data']['pressure'] = pressure_line
                
                field_dict = {'pressure': pressure_line}
                session.data['fields'].update(field_dict)
                
                self.agent.publish_to_feed('pressure', data)
                
                session.data['fields'].update({'timestamp': current_time})
                time.sleep(sleep_time)
                
                if params['test_mode']:
                    break
            
            self.agent.feeds['pressure'].flush_buffer()
        return True, 'Acquisition exited cleanly'


    def stop_acq(self, session, params=None):
        if self.take_data:
            self.take_data = False
            self.gauge.close()
            return True, 'Requested to stop taking data.'
        else:
            return False, 'Acq is not currently running.'

    
def make_parser(parser=None):
    """
    Makes an understandable accumulation of arguments for agent with site_config
    """
    if parser is None:
        parser = argparse.ArgumentParser()

    pgroup = parser.add_argument_group('Agent Options')
    pgroup.add_argument('--port', type=str, help="Path to USB for the Teledyne Pressure Gauge")
    pgroup.add_argument('--baud', type=int, default =19200)
    pgroup.add_argument('--sampling_frequency', type=float, help='Sampling frequency for data acquisition', default = 2.5)
    pgroup.add_argument("--mode", type=str, default='acq', choices=['acq', 'test'])

    return parser
    
def main(args = None):
        parser = make_parser()
        args = site_config.parse_args(agent_class='TeledyneAgent',
                                      parser=parser,
                                      args=args)
        
        init_params = True
        if args.mode == 'test':
            init_params = {'test_mode': True}
        
        agent, runner = ocs_agent.init_site_agent(args)
        teledyne_agent = Teledyne_Agent(agent, args.port, args.sampling_frequency)
        agent.register_process('acq', teledyne_agent.acq,
                             teledyne_agent.stop_acq,
                             startup= init_params)
        agent.register_task('close', teledyne_agent.stop_acq)
        runner.run(agent, auto_reconnect=True)

if __name__ == '__main__':
    main()

