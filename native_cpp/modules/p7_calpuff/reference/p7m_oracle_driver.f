c-----------------------------------------------------------------------
      program p7m_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7M FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7m_source_anchor.py:
c       munu bi bji bjil ireg rotate erfdif sigma ctrec puffc lower ctsg
c
c --- The driver supplies the routines the extracted units reference but
c     which are NOT part of this port: SIGTY/SIGTZ (deterministic stubs,
c     mirrored by the C++ test so both sides see identical curve
c     behaviour) and CTPAR/UPPER (hard failures, since every parity case
c     must stay on the reconstructed branch).
c
c --- The /CONST/ block is initialized exactly as the vendor CTINIT does
c     (calpuff.for L22412-22434). RT2PI is deliberately NOT set, because
c     CTINIT does not set it either (see reference/p7m_source_anchor.py).
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode  1: icase muflag xbi ybi r                        -> mu nu
c     mode  2: icase afac argm argp                          -> b
c     mode  3: icase ak dm dp d0 eoimh eoiph ej szesq szosq szpsq -> bj
c     mode  4: icase ak b1 ej eoi szsq szosq szpsq           -> bj
c     mode  5: icase itype zpuff ws t s1 tstart s2 tstep sr frac -> sigma
c     mode  6: icase x x12 x23                               -> ireg
c     mode  7: icase <state>                                 -> ctrec outputs
c     mode  8: icase <state> imode zpole dpole               -> c
c     mode  9: icase <state>                                 -> c
c     mode 10: icase <state> ipin ihin tin                   -> conc cflat
c     mode 11: (no input)                                    -> the /CONST/ values
c
c --- <state> is 46 real numbers in this fixed order:
c     tstart tstep u q zlid frac sz1 sz2 sy1 sy2 szr syr szmn symn
c     hd ubyn h zgrid xc yc rotflo rotang alfw beta cbeta d baxi r
c     x12f x23f xob xp yp zpuff xpf ypf t12p timpg szimpg syimpg
c     xr yr zrec isc ih ip
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'const.puf'
      include 'ctpass.puf'
c
      integer mode,ios,icase,muflag,itype,imode,ipin,ihin
      real xbi,ybi,rr,mu,nu
      real afac,argm,argp,b
      real ak,dm,dp,d0,eoimh,eoiph,ej,bj,b1,eoi
c --- NOTE: the mode 5 locals must not collide with /CTPASS/ names; WS is an
c     array there, so a scalar named WS would silently read MXLEV values.
      real sigzp,sigws,sigt,sigs1,sigt0,sigs2,sigdt,sigsr
      real sigfr,sig,sigma
      real xx,x12in,x23in
      real st(46)
      real zpole,dpole,cc,conc,cflat,tin
c --- XRB/YRB are locals of the vendor CTREC (they are not in /CTPASS/), so the
c     driver recomputes them with the same ROTATE call for the report.
      real xrbc,yrbc
      integer i
c
c --- /CONST/ exactly as CTINIT sets it; RT2PI intentionally absent.
      zero=0.
      one=1.
      two=2.
      three=3.
      four=4.
      half=0.5
      twoby3=two/three
      rt2=sqrt(two)
      pi=3.1415927
      rtpi=sqrt(pi)
      pii=one/pi
      rtpii=one/rtpi
      piby2=half*pi
      twopi=two*pi
      dtor=pi/180.
      small=.000001
      expmax=69.
      alphai=1.20
      hslfac=0.05
      epsint=0.01
      epsrefl=0.01
      mxrefl=50
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7M oracle: missing mode'
c
      if(mode.eq.11)then
         write(*,'(a,es20.12)') 'P7M_CONST_RT2PI ',rt2pi
         write(*,'(a,es20.12)') 'P7M_CONST_SMALL ',small
         write(*,'(a,es20.12)') 'P7M_CONST_EXPMAX ',expmax
         write(*,'(a,es20.12)') 'P7M_CONST_EPSREFL ',epsrefl
         write(*,'(a,i8)') 'P7M_CONST_MXREFL ',mxrefl
         goto 999
      endif
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,muflag,xbi,ybi,rr
         if(ios.ne.0) goto 999
         call munu(muflag,xbi,ybi,rr,mu,nu)
         write(*,'(i8,2(1x,es20.12))') icase,mu,nu
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,afac,argm,argp
         if(ios.ne.0) goto 999
         call bi(afac,argm,argp,b)
         write(*,'(i8,1x,es20.12)') icase,b
         goto 20
      endif
c
      if(mode.eq.3)then
 30      read(*,*,iostat=ios) icase,ak,dm,dp,d0,eoimh,eoiph,ej,
     &                      szesq,szosq,szpsq
         if(ios.ne.0) goto 999
         call bji(ak,dm,dp,d0,eoimh,eoiph,ej,bj)
         write(*,'(i8,1x,es20.12)') icase,bj
         goto 30
      endif
c
      if(mode.eq.4)then
 40      read(*,*,iostat=ios) icase,ak,b1,ej,eoi,szsq,szosq,szpsq
         if(ios.ne.0) goto 999
         call bjil(ak,b1,ej,eoi,bj)
         write(*,'(i8,1x,es20.12)') icase,bj
         goto 40
      endif
c
      if(mode.eq.5)then
 50      read(*,*,iostat=ios) icase,itype,sigzp,sigws,sigt,sigs1,sigt0,
     &                      sigs2,sigdt,sigsr,sigfr
         if(ios.ne.0) goto 999
         sig=sigma(itype,sigzp,sigws,sigt,sigs1,sigt0,sigs2,sigdt,sigsr,
     &             sigfr)
         write(*,'(i8,1x,es20.12)') icase,sig
         goto 50
      endif
c
      if(mode.eq.6)then
 60      read(*,*,iostat=ios) icase,xx,x12in,x23in
         if(ios.ne.0) goto 999
         write(*,'(i8,1x,i4)') icase,ireg(xx,x12in,x23in)
         goto 60
      endif
c
 70   continue
      read(*,*,iostat=ios) icase,(st(i),i=1,46)
      if(ios.ne.0) goto 999
      call setstate(st)
c
c --- PUFFC and LOWER read CTREC's outputs (XRF/YRF/XRE/YRE/T12RU/T12RL/IREGU/
c     IREGL) from /CTPASS/, exactly as the vendor CTSG does before calling them.
      if(mode.eq.8 .OR. mode.eq.9) call ctrec
c
      if(mode.eq.7)then
         call ctrec
         call rotate(xrf,yrf,beta,xrbc,yrbc)
         write(*,'(i8,8(1x,es20.12),2(1x,i4))') icase,xrf,yrf,
     &      xre,yre,xrbc,yrbc,t12ru,t12rl,iregu,iregl
         goto 70
      endif
c
      if(mode.eq.8)then
         read(*,*,iostat=ios) imode,zpole,dpole
         if(ios.ne.0) stop 'P7M oracle: missing puffc arguments'
         call puffc(imode,zpole,dpole,cc)
         write(*,'(i8,1x,es20.12)') icase,cc
         goto 70
      endif
c
      if(mode.eq.9)then
         call lower(cc)
         write(*,'(i8,1x,es20.12)') icase,cc
         goto 70
      endif
c
      read(*,*,iostat=ios) ipin,ihin,tin
      if(ios.ne.0) stop 'P7M oracle: missing ctsg arguments'
      xrctm(1)=st(41)
      yrctm(1)=st(42)
      call ctsg(.FALSE.,1,ipin,st(4),st(3),0.0,st(5),st(32),st(33),
     &          st(34),INT(st(44)),st(43),ihin,st(2),tin,st(7),st(8),
     &          st(9),st(10),st(11),st(12),st(13),st(14),st(6),
     &          conc,cflat)
      write(*,'(i8,2(1x,es20.12))') icase,conc,cflat
      goto 70
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine setstate(st)
c-----------------------------------------------------------------------
c --- Transfer the fixed-order state line into the /CTPASS/ common block.
      include 'params.puf'
      include 'ctpass.puf'
      real st(46)
      tstart=st(1)
      tstep=st(2)
      u=st(3)
      q=st(4)
      zlid=st(5)
      frac=st(6)
      sz1=st(7)
      sz2=st(8)
      sy1=st(9)
      sy2=st(10)
      szr=st(11)
      syr=st(12)
      szmn=st(13)
      symn=st(14)
      hd=st(15)
      ubyn=st(16)
      h=st(17)
      ih=INT(st(45))
      ip=INT(st(46))
      zgrid(ih)=st(18)
      xc(ih)=st(19)
      yc(ih)=st(20)
      hda(ih)=st(15)
      ubyna(ih)=st(16)
      relief(ih)=st(17)
      rotflo=st(21)
      rotang=st(22)
      alfw=st(23)
      beta=st(24)
      cbeta=st(25)
      d=st(26)
      baxi=st(27)
      r=st(28)
      x12f=st(29)
      x23f=st(30)
      xob=st(31)
      xp=st(32)
      yp=st(33)
      zpuff=st(34)
      xpf=st(35)
      ypf=st(36)
      t12p=st(37)
      timpg=st(38)
      szimpg=st(39)
      syimpg=st(40)
      xr=st(41)
      yr=st(42)
      zrec=st(43)
      isc=INT(st(44))
      ldb=.FALSE.
      return
      end
c-----------------------------------------------------------------------
      subroutine sigty(sigy0,dxkm,dt,sigy,virty,virdy)
c-----------------------------------------------------------------------
c --- Deterministic SIGTY stub. The C++ parity test injects the identical
c     formula, so the ported SIGMA wrapper is exercised against the
c     UNMODIFIED vendor SIGMA with a curve pair that is identical on both
c     sides. The vendor SIGTY/SIGTZ themselves are covered by P7D.
      real sigy0,dxkm,dt,sigy,virty,virdy
      sigy=sigy0+0.5*dxkm+0.1*dt
      virdy=sigy0*0.01
      virty=sigy0*0.5
      return
      end
c-----------------------------------------------------------------------
      subroutine sigtz(sigz0,dxkm,dt,zht,sigz,virtz,virdz)
c-----------------------------------------------------------------------
      real sigz0,dxkm,dt,zht,sigz,virtz,virdz
      sigz=sigz0+0.3*dxkm+0.2*dt+0.01*zht
      virdz=sigz0*0.02
      virtz=sigz0*0.4
      return
      end
c-----------------------------------------------------------------------
      subroutine ctpar
c-----------------------------------------------------------------------
      write(*,*) 'P7M oracle: CTPAR must not be called by a parity case'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine upper(c)
c-----------------------------------------------------------------------
      real c
      write(*,*) 'P7M oracle: UPPER must not be called by a parity case'
      stop 9
      end
