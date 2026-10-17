c-----------------------------------------------------------------------
      program p7q_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7Q FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the generated harnesses extracted by
c     reference/p7q_source_anchor.py, which wrap the VERBATIM SETPUF
c     sigma-update statements.
c
c --- The driver supplies SIGTY and SIGTZ as deterministic stubs that the
c     C++ test mirrors exactly (the vendor curves themselves carry the P7D
c     parity evidence).
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase sigyb sigzb zpuff tmid dmidkm icode
c             -> icase syb1 sym1 sye1 vtyb1 vtym1 vtye1 vdyb1 vdym1 vdye1
c                szb1 szm1 sze1 vtzb1 vtzm1 vtze1 vdzb1 vdzm1 vdze1
c     mode 2: icase syb1 sym1 sye1 bidfnl sy0sq lcalm
c             -> icase syb1 sym1 sye1 sysq sigyb_stored sy0_stored
c     mode 3: icase szb1 szm1 sze1 bidfnl lcalm
c             -> icase szb1 szm1 sze1 sigzb_stored sz0_stored
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'puff.puf'
c
      integer mode,ios,icase,icode_i,lcalm_i
      real syb1_i,sym1_i,sye1_i,bidfnl_i,sy0sq_i
      real sigyb_i,sigzb_i,zpuff_i,tmid_i,dmidkm_i
      real syb1_o,sym1_o,sye1_o,vtyb1_o,vtym1_o,vtye1_o
      real vdyb1_o,vdym1_o,vdye1_o,szb1_o,szm1_o,sze1_o
      real vtzb1_o,vtzm1_o,vtze1_o,vdzb1_o,vdzm1_o,vdze1_o
      real sysq_o,sigyb_o,sy0_o,sigzb_o,sz0_o
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7Q oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,sigyb_i,sigzb_i,zpuff_i,tmid_i,
     &                      dmidkm_i,icode_i
         if(ios.ne.0) goto 999
         call p7q_sigma(sigyb_i,sigzb_i,zpuff_i,tmid_i,dmidkm_i,icode_i,
     &                  syb1_o,sym1_o,sye1_o,vtyb1_o,vtym1_o,vtye1_o,
     &                  vdyb1_o,vdym1_o,vdye1_o,szb1_o,szm1_o,sze1_o,
     &                  vtzb1_o,vtzm1_o,vtze1_o,vdzb1_o,vdzm1_o,vdze1_o)
         write(*,'(i8,18(1x,es20.12))') icase,syb1_o,sym1_o,sye1_o,
     &      vtyb1_o,vtym1_o,vtye1_o,vdyb1_o,vdym1_o,vdye1_o,szb1_o,
     &      szm1_o,sze1_o,vtzb1_o,vtzm1_o,vtze1_o,vdzb1_o,vdzm1_o,
     &      vdze1_o
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,syb1_i,sym1_i,sye1_i,bidfnl_i,
     &                      sy0sq_i,lcalm_i
         if(ios.ne.0) goto 999
         call p7q_sigma_y(syb1_i,sym1_i,sye1_i,bidfnl_i,sy0sq_i,
     &                    MERGE(.TRUE.,.FALSE.,lcalm_i.EQ.1),
     &                    sysq_o,sigyb_o,sy0_o)
         write(*,'(i8,6(1x,es20.12))') icase,syb1_i,sym1_i,sye1_i,
     &      sysq_o,sigyb_o,sy0_o
         goto 20
      endif
c
 30   continue
      read(*,*,iostat=ios) icase,szb1_i,szm1_i,sze1_i,bidfnl_i,lcalm_i
      if(ios.ne.0) goto 999
      call p7q_sigma_z(szb1_i,szm1_i,sze1_i,bidfnl_i,
     &                 MERGE(.TRUE.,.FALSE.,lcalm_i.EQ.1),sigzb_o,sz0_o)
      write(*,'(i8,5(1x,es20.12))') icase,szb1_i,szm1_i,sze1_i,sigzb_o,
     &   sz0_o
      goto 30
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine sigty(sigy0,dxkm,dt,sigy,virty,virdy)
c-----------------------------------------------------------------------
c --- Deterministic SIGTY stub (the C++ test injects the identical formula).
      real sigy0,dxkm,dt,sigy,virty,virdy
      sigy=sigy0+0.5*dxkm+0.1*dt
      virdy=sigy0*0.01+0.002*dxkm
      virty=sigy0*0.5+2.0*dt
      return
      end
c-----------------------------------------------------------------------
      subroutine sigtz(sigz0,dxkm,dt,zht,sigz,virtz,virdz)
c-----------------------------------------------------------------------
      real sigz0,dxkm,dt,zht,sigz,virtz,virdz
      sigz=sigz0+0.3*dxkm+0.2*dt+0.01*zht
      virdz=sigz0*0.02+0.003*dxkm
      virtz=sigz0*0.4+3.0*dt
      return
      end
