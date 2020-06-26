
import deepSI
import numpy as np
from matplotlib import pyplot as plt

def load_system_data(file):
    outfile = dict(np.load(file,allow_pickle=True))
    def get_sys_data(data):
        for k in data:
            if data[k].shape==tuple(): #if it is a single element
                data[k] = data[k].tolist()
        return System_data(**data)
    if outfile.get('sdl') is not None: #list of data
        return System_data_list(sys_data_list = [get_sys_data(o) for o in outfile['sdl']])
    else:
        return get_sys_data(outfile)

class System_data(object):
    """sys_data.u will always"""
    def __init__(self, u=None, y=None, x=None, cheat_n=0, normed=False):
        super(System_data, self).__init__()
        assert (y is not None) or (u is not None), 'either y or u requires to be not None or'
        N_samples = len(u) if u is not None else len(y)
        
        self.u = np.array(u) if u is not None else np.zeros((N_samples,0)) #if y exists than u will always exists
        self.x = np.array(x) if x is not None else None
        self.y = np.array(y) if y is not None else None
        self.cheat_n = cheat_n #when the real simulation starts, used in evaluation
        self.multi_u = self.u.ndim>1
        self.multi_y = self.y.ndim>1 if self.y is not None else True
        self.normed = normed

        #checks
        if self.y is not None:
            assert self.u.shape[0]==self.y.shape[0], f'{self.u.shape[0]}!={self.y.shape[0]}'
        if self.x is not None: 
            assert self.x.shape[0]==self.y.shape[0]

    @property
    def N_samples(self):
        return self.u.shape[0]
    @property
    def ny(self):
        return (None if self.y.ndim==1 else self.y.shape[1]) if self.y is not None else 0
    @property
    def nu(self):
        return None if self.u.ndim==1 else self.u.shape[1]


    ############################
    ###### Transformations #####
    ############################
    def to_IO_data(self,na=10,nb=10):
        '''Input output data structure will return 
            hist, Y
            hist = [[u[k-nb:k].flat,y[k-na:k].flat]]_k
            Y = y[k]'''
        u, y = np.copy(self.u), np.copy(self.y)
        hist = []
        Y = []
        for k in range(max(na,nb),len(u)):
            hist.append(np.concatenate((u[k-nb:k].flat,y[k-na:k].flat))) #size = nb*nu + na*ny
            Y.append(y[k])
        return np.array(hist), np.array(Y)

    def to_hist_future_data(self,na=10,nb=10,nf=5):
        '''convertes data set to  a system of 
        yhist = [y[k-na],....,y[k-1]]
        uhist = [u[k-nb],....,u[k-1]]
        yfuture = [y[k],....,y[k+nf-1]]
        ufuture = [u[k],....,u[k+nf-1]]
        nf = n_future
        returns yhist,uhist,yfuture,ufuture
        
        made for simulation error and multi in and output data sets
        '''
        u, y = np.copy(self.u), np.copy(self.y)
        yhist = []
        uhist = []
        ufuture = []
        yfuture = []
        for k in range(max(nb,na)+nf,len(u)+1):
            yhist.append(y[k-na-nf:k-nf])
            uhist.append(u[k-nb-nf:k-nf])
            yfuture.append(y[k-nf:k])
            ufuture.append(u[k-nf:k])
        return np.array(uhist),np.array(yhist),np.array(ufuture),np.array(yfuture)


    def to_ss_data(self,nf=20):
        u, y = np.copy(self.u), np.copy(self.y)
        ufuture = []
        yfuture = []
        for k in range(nf,len(u)+1):
            yfuture.append(y[k-nf:k])
            ufuture.append(u[k-nf:k])
        return np.array(ufuture), np.array(yfuture)

    def to_encoder_data(self,na=10,nb=10,nf=5):
        '''convertes data set to  a system of 
        hist = [u[k-nb:k].flat,y[k-na:k].flat]
        yfuture = [y[k],....,y[k+nf-1]]
        ufuture = [u[k],....,u[k+nf-1]]
        nf = n_future
        returns yhist,uhist,yfuture,ufuture
        
        made for simulation error and multi in and output data sets
        '''
        u, y = np.copy(self.u), np.copy(self.y)
        hist = []
        ufuture = []
        yfuture = []
        for k in range(max(nb,na)+nf,len(u)+1):
            hist.append(np.concatenate((u[k-nb:k].flat,y[k-na:k].flat)))
            yfuture.append(y[k-nf:k])
            ufuture.append(u[k-nf:k])
        return np.array(hist),np.array(ufuture),np.array(yfuture)



    def save(self,file):
        '''Saves data'''
        np.savez(name, u=self.u, x=self.x, y=self.y, cheat_n=self.cheat_n, normed=self.normed)

    def __repr__(self):
        return f'System_data of length: {self.N_samples} nu={self.nu} ny={self.ny} normed={self.normed}'

    def plot(self,show=False):
        '''Very simple plotting function'''
        plt.ylabel('y' if self.y is not None else 'u')
        plt.xlabel('t')
        plt.plot(self.y if self.y is not None else self.u)
        if show: plt.show()

    def BFR(self,real,multi_average=True):
        '''Best Fit Rate'''
        # y, yhat = real.y[self.cheat_n:], self.y[self.cheat_n:]
        # return 100*(1 - np.sum((y-yhat)**2)**0.5/np.sum((y-np.mean(y))**2)**0.5)
        return 100*(1 - self.NRMS(real,multi_average=multi_average))

    def NRMS(self,real,multi_average=True):
        RMS = self.RMS(real,multi_average=True) #always true
        y_std = np.std(real.y,axis=0)
        return np.mean(RMS/y_std) if multi_average else RMS/y_std

    def RMS(self,real, multi_average=True):
        '''Root mean square error'''
        #Variance accounted for
        #y output system
        #yhat output model
        y, yhat = real.y[self.cheat_n:],self.y[self.cheat_n:]
        return np.mean((y-yhat)**2)**0.5

    def VAF(self,real,multi_average=True):
        '''Variance accounted for'''
        # y output system
        # yhat output model
        # also known as R^2
        # y, yhat = real.y[self.cheat_n:],self.y[self.cheat_n:]
        # return 100*(1-(np.var(y-yhat)/np.var(y)))
        return 100*(1-self.NRMS(real,multi_average=multi_average**2))

    def __sub__(self,other): #todo correct this
        if isinstance(other,(float,int,np.ndarray)):
            return System_data(u=self.u, x=self.x, y=self.y-other, cheat_n=self.cheat_n)
        elif isinstance(other,System_data):
            assert len(self.y)==len(other.y), 'both arguments need to be the same length'
            return System_data(u=self.u, x=self.x, y=self.y-other.y, cheat_n=self.cheat_n)

    def train_test_split(self,split_fraction=0.25):
        '''return 2 data sets of length n*(1-split_fraction) and n*split_fraction respectively (left, right) split'''
        n_samples = self.u[self.cheat_n:].shape[0]
        split_n = int(n_samples*(1 - split_fraction))
        ul,ur,yl,yr = self.u[self.cheat_n:split_n], self.u[self.cheat_n+split_n:], \
                        self.y[self.cheat_n:split_n], self.y[self.cheat_n+split_n:]
        if self.x is None:
            xl,xr = None,None
        else:
            xl,xr = self.x[:split_n], self.x[split_n:]
        left_data = System_data(u=ul, x=xl, y=yl, normed=self.normed)
        right_data = System_data(u=ur, x=xr, y=yr, normed=self.normed)
        return left_data, right_data

    def __getitem__(self,arg):
        assert isinstance(arg,slice),'Please use a slice (e.g. sys_data[20:100]) or use sys_data.u or sys_data.y'
        start, stop, step = arg.indices(self.u.shape[0])
        cheat_n = max(0,self.cheat_n-start)
        unew = self.u[arg]
        ynew = self.y[arg] if self.y is not None else None
        xnew = self.x[arg] if self.x is not None else None
        return System_data(u=unew, y=ynew, x=xnew, cheat_n=cheat_n, normed=self.normed)
    
    def __len__(self):
        return self.N_samples

    def down_sample_by_average(self,factor):
        assert isinstance(factor, int) 
        L = self.N_samples
        n = (L//factor)*factor
        u,y = self.u, self.y
        if u.ndim==1:
            u = np.mean(self.u[:n].reshape((-1,factor)),axis=1)
        else:
            u = np.stack([np.mean(self.u[:n,i].reshape((-1,factor)),axis=1) for i in range(self.u.shape[1])],axis=1)
        if y.ndim==1:
            y = np.mean(self.y[:n].reshape((-1,factor)),axis=1)
        else:
            y = np.stack([np.mean(self.y[:n,i].reshape((-1,factor)),axis=1) for i in range(self.y.shape[1])],axis=1)
        return System_data(u=u,y=y,x=self.x[::factor] if self.x is not None else None,cheat_n=self.cheat_n,normed=self.normed)

class System_data_list(object):
    def __init__(self,sys_data_list):
        assert len(sys_data_list)>0, 'At least one data set should be provided'
        ny = sys_data_list[0].ny
        nu = sys_data_list[0].nu
        normed = sys_data_list[0].normed
        for sys_data in sys_data_list:
            assert isinstance(sys_data,System_data)
            assert sys_data.ny==ny
            assert sys_data.nu==nu
            assert sys_data.normed==normed
        self.sdl = sys_data_list
        self.normed = normed
    @property
    def N_samples(self):
        return sum(sys_data.u.shape[0] for sys_data in self.sdl)
    @property
    def ny(self):
        return self.sdl[0].ny
    @property
    def nu(self):
        return self.sdl[0].nu
    @property
    def y(self): #concatenate or list of lists
        return np.concatenate([sd.y for sd in self.sdl],axis=0)
    @property
    def u(self): #concatenate or list of lists
        return np.concatenate([sd.u for sd in self.sdl],axis=0)

    ## Transformations ##
    def to_IO_data(self,na=10,nb=10):
        #normed check?
        out = [sys_data.to_IO_data(na=na,nb=nb) for sys_data in self.sdl]  #((I,ys),(I,ys))
        return [np.concatenate(o,axis=0) for o in  zip(*out)] #(I,I,I),(ys,ys,ys)

    def to_hist_future_data(self,na=10,nb=10,nf=5):
        out = [sys_data.to_hist_future_data(na=na,nb=nb,nf=nf) for sys_data in self.sdl]  #((I,ys),(I,ys))
        return [np.concatenate(o,axis=0) for o in  zip(*out)] #(I,I,I),(ys,ys,ys)

    def to_ss_data(self,nf=20):
        out = [sys_data.to_ss_data(nf=nf) for sys_data in self.sdl]  #((I,ys),(I,ys))
        return [np.concatenate(o,axis=0) for o in  zip(*out)] #(I,I,I),(ys,ys,ys)


    def to_encoder_data(self,na=10,nb=10,nf=5):
        out = [sys_data.to_hist_future_data(na=na,nb=nb,nf=nf) for sys_data in self.sdl]  #((I,ys),(I,ys))
        return [np.concatenate(o,axis=0) for o in  zip(*out)] #(I,I,I),(ys,ys,ys)

    def save(self,file):
        '''Saves data'''
        out = [dict(u=sd.u, x=sd.x, y=sd.y, cheat_n=sd.cheat_n, normed=sd.normed) for sd in self.sdl]
        np.savez(name, sdl=out)

    def __repr__(self):
        return f'System_data_list with {len(self.sdl)} series and total length {self.N_samples}, nu={self.nu}, ny={self.ny}, normed={self.normed} lengths={[sd.N_samples for sd in self.sdl]}'

    def plot(self,show=False):
        '''Very simple plotting function'''
        plt.ylabel('y' if self.sdl[0].y is not None else 'u')
        plt.xlabel('t')
        for sd in self.sdl:
            plt.plot(sd.y if sd.y is not None else sd.u)
        if show: plt.show()

    def weighted_mean(self,vals):
        return np.average(vals,axis=0,weights=[sd.N_samples for sd in self.sdl])

    def BFR(self,real,multi_average=True):
        return self.weighted_mean([sd.BFR(sdo,multi_average=multi_average) for sd,sdo in zip(self.sdl,real.sdl)])

    def NRMS(self,real,multi_average=True):
        return self.weighted_mean([sd.NRMS(sdo,multi_average=multi_average) for sd,sdo in zip(self.sdl,real.sdl)])

    def RMS(self,real, multi_average=True):
        return self.weighted_mean([sd.RMS(sdo,multi_average=multi_average) for sd,sdo in zip(self.sdl,real.sdl)])

    def VAF(self,real,multi_average=True):
        return self.weighted_mean([sd.VAF(sdo,multi_average=multi_average) for sd,sdo in zip(self.sdl,real.sdl)])

    def __sub__(self,other):
        if isinstance(other,(float,int,np.ndarray,System_data)):
            if isinstance(other, System_data):
                other = other.y
            return System_data_list([System_data(u=sd.u, x=sd.x, y=sd.y-other, cheat_n=sd.cheat_n) for sd in self.sdl])
        elif isinstance(other,System_data_list):            
            return System_data_list([System_data(u=sd.u, x=sd.x, y=sd.y-sdo.y, cheat_n=sd.cheat_n) for sd,sdo in zip(self.sdl,other.sdl)])

    def train_test_split(self,split_fraction=0.25):
        '''return 2 data sets of length n*(1-split_fraction) and n*split_fraction respectively (left, right) split'''
        out = list(zip(*[sd.train_test_split(split_fraction=split_fraction) for sd in self.sdl]))
        left,right = System_data_list(out[0]), System_data_list(out[1])
        return left, right

    def __getitem__(self,arg): #by data set or by time?
        '''Will use time as an argument, use self.sdl[arg]'''
        if isinstance(arg,tuple) and len(arg)>1: #than it has two arguments
            assert len(arg)==2, f'what would {arg} for length>2 even do?'
            sdl_sub = self.sdl[arg[1]]
            if isinstance(sdl_sub,list):
                return System_data_list([sd[arg[0]] for sd in sdl_sub])
            else:
                return sdl_sub[arg[0]]
        else:
            return System_data_list([sd[arg] for sd in self.sdl])

    def __len__(self):
        return self.N_samples

    def down_sample_by_average(self,factor):
        return System_data_list([sd.down_sample_by_average(factor) for sd in self.sdl])

class System_data_norm(object):
    '''Utility to normalize training data before fitting'''
    def __init__(self, u0=0, ustd=1, y0=0, ystd=1):
        self.u0 = u0
        self.ustd = ustd
        self.y0 = y0
        self.ystd = ystd

    def make_training_data(self,sys_data):
        if isinstance(sys_data,(list,tuple)):
            out = [self.make_training_data(s) for s in sys_data]
            return [np.concatenate(a,axis=0) for a in zip(*out)] #transpose + concatenate
        return sys_data.u, sys_data.y

    def fit(self,sys_data):
        #finds   self.y0,self.ystd,self.u0,self.ustd
        u, y = self.make_training_data(sys_data)
        self.u0 = np.mean(u,axis=0)
        self.ustd = np.std(u,axis=0)
        self.y0 = np.mean(y,axis=0)
        self.ystd = np.std(y,axis=0)
        
    def transform(self,sys_data):
        '''Transform the data by 
           u <- (sys_data.u-self.u0)/self.ustd
           y <- (sys_data.y-self.y0)/self.ystd'''
        if isinstance(sys_data,(list,tuple)):
            return [self.transform(s) for s in sys_data] #conversion?
        elif isinstance(sys_data,System_data_list):
            return System_data_list([self.transform(s) for s in sys_data.sdl])
        
        assert sys_data.normed==False, 'System_data is already normalized'
        
        if isinstance(sys_data,System_data):
            u_transformed = (sys_data.u-self.u0)/self.ustd if sys_data.u is not None else None
            y_transformed = (sys_data.y-self.y0)/self.ystd if sys_data.y is not None else None

            return System_data(u=u_transformed,x=sys_data.x,y=y_transformed, \
                cheat_n=sys_data.cheat_n,normed=True)
        else:
            assert False

    def inverse_transform(self,sys_data):
        '''Inverse Transform the data by 
           u <- sys_data.u*self.ustd+self.u0
           y <- sys_data.y*self.ystd+self.y0'''
        if isinstance(sys_data,(list,tuple)):
            return [self.inverse_transform(s) for s in sys_data]
        elif isinstance(sys_data,System_data_list):
            return System_data_list([self.inverse_transform(s) for s in sys_data.sdl])
        assert sys_data.normed==True, 'System_data is already un-normalized'
        if isinstance(sys_data,System_data):
            u_inv_transformed, y_inv_transformed = sys_data.u*self.ustd+self.u0, sys_data.y*self.ystd+self.y0
            return System_data(u=u_inv_transformed,x=sys_data.x,y=y_inv_transformed,
            cheat_n=sys_data.cheat_n,normed=False)
        else:
            assert False

    def save_system(self):
        #pickle is the easiest
        raise NotImplementedError

    def load_system(self):
        raise NotImplementedError

    def __repr__(self):
        return f'norm: u0={self.u0},ustd={self.ustd},y0={self.y0},ystd={self.ystd}'


if __name__=='__main__':
    sys_data = System_data(u=np.random.normal(scale=2,size=(100,2)),y=np.random.normal(scale=1.5,size=(100,2)))
    sys_data2 = System_data(u=np.random.normal(size=(100,2)),y=np.random.normal(size=(100,2)))
    sys_data3 = System_data(u=np.random.normal(size=(100,2)),y=np.random.normal(size=(100,2)))
    print(sys_data.NRMS(sys_data2,multi_average=False))
    print(sys_data.to_encoder_data(10,10,10)[0].shape)
    print(len(sys_data2[10:20]))
    sdl = System_data_list([sys_data,sys_data2,sys_data3])
    print(sdl.to_encoder_data(9)[0].shape)
    print(len(sdl))
    # sdl.plot(show=True)
    print(sdl.train_test_split())
    print(sdl.down_sample_by_average(10))
    print(sdl.VAF(sdl))
    norm = System_data_norm()
    norm.fit(sdl)
    sdl2 = norm.transform(sdl)
    sdl3 = norm.inverse_transform(sdl2)
    print(sdl2.NRMS(sdl))
    print(sdl3.NRMS(sdl))
    print(np.std(sdl2.sdl[0].y,axis=0))

    # class Test_class(object):
    #     def __init__(self):
    #         pass
    #     def __getitem__(self,arg):
    #         print(arg)
    # T = Test_class()
    # T[1]
    print(sdl[:-10,-1])
    # sys_data.plot()
    # plt.show()