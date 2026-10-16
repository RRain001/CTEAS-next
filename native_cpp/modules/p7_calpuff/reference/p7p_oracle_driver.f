c-----------------------------------------------------------------------
      program p7p_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7P FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor unit `setcsig` and the
c     generated harnesses extracted by reference/p7p_source_anchor.py:
c       p7p_step   (verbatim SETPUF step-bookkeeping statements)
c       p7p_update (verbatim SETPUF state-update statements)
c
c --- The driver supplies SIGTY (deterministic stub, mirrored by the C++
c     test so both sides see identical curve behaviour) and TAULY (hard
c     failure, since MTAULY=1 is off the locked deck's path).
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase xtotb tmtotb distm tsamp dm2km ws wscalm idw0 xfinal
c             idopty idoptz
c             -> icase idopty idoptz xttb1 xtte1 tb1 te1 dmidkm tmid uavg
c                ukps lcalm idw0 xfinal
c     mode 2: icase ze1 vgrav mtilt tsamp distm xtotb tmtotb xnew ynew
c             -> icase ze1 xtotb tmtotb xpb ypb zpb
c     mode 3: icase idopty idoptz iru uavg kst el bvf tsigv tsigw symin
c             szmin zht zmix ix iy md mhftsz mtauly
c             -> icase the /CSIGMA/ state + the stub SIGTY in/out
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'csigma.puf'
      include 'flags.puf'
c
      common/p7pdbg/sigty_in1,sigty_in2,sigty_in3,sigty_out1,sigty_out2,
     &              sigty_out3
      real sigty_in1,sigty_in2,sigty_in3,sigty_out1,sigty_out2
      real sigty_out3
c
      integer mode,ios,icase,idopty_i,idoptz_i,idw0_i,mtilt_i,iru_i
      integer kst_i,ix_i,iy_i,md_i,mhftsz_i,mtauly_i,idopty_o,idoptz_o
      integer idw0_o
      real xtotb_i,tmtotb_i,distm_i,tsamp_i,dm2km_i,ws_i,wscalm_i
      real xfinal_i,xttb1_o,xtte1_o,tb1_o,te1_o,dmidkm_o,tmid_o
      real uavg_o,ukps_o,xfinal_o
      logical lcalm_o
      real ze1_i,vgrav_i,xtotb_o,tmtotb_o,xpb_o,ypb_o,zpb_o
      real xnew_i,ynew_i
      real uavg_i,el_i,bvf_i,tsigv_i,tsigw_i,symin_i,szmin_i
      real zht_i,zmix_i,dum_o
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7P oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,xtotb_i,tmtotb_i,distm_i,tsamp_i,
     &                      dm2km_i,ws_i,wscalm_i,idw0_i,xfinal_i,
     &                      idopty_i,idoptz_i
         if(ios.ne.0) goto 999
         call p7p_step(xtotb_i,tmtotb_i,distm_i,tsamp_i,dm2km_i,ws_i,
     &                 wscalm_i,idw0_i,xfinal_i,idopty_i,idoptz_i,
     &                 idopty_o,idoptz_o,
     &                 xttb1_o,xtte1_o,tb1_o,te1_o,dmidkm_o,tmid_o,
     &                 uavg_o,ukps_o,lcalm_o,idw0_o,xfinal_o)
         write(*,'(i8,3(1x,i8),6(1x,es20.12),1x,i4,3(1x,es20.12))')
     &      icase,idopty_o,idoptz_o,idw0_o,xttb1_o,xtte1_o,tb1_o,te1_o,
     &      dmidkm_o,tmid_o,INT(MERGE(1.0,0.0,lcalm_o)),uavg_o,ukps_o,
     &      xfinal_o
         goto 10
      endif
c
      if(mode.eq.2)then
 20      read(*,*,iostat=ios) icase,ze1_i,vgrav_i,mtilt_i,tsamp_i,
     &                      distm_i,xtotb_i,tmtotb_i,xnew_i,ynew_i
         if(ios.ne.0) goto 999
         call p7p_update(ze1_i,vgrav_i,mtilt_i,tsamp_i,distm_i,
     &                   xtotb_i,tmtotb_i,xnew_i,ynew_i,ze1_i,xtotb_o,
     &                   tmtotb_o,xpb_o,ypb_o,zpb_o)
         write(*,'(i8,6(1x,es20.12))') icase,ze1_i,xtotb_o,tmtotb_o,
     &      xpb_o,ypb_o,zpb_o
         goto 20
      endif
c
 30   continue
      read(*,*,iostat=ios) icase,idopty_i,idoptz_i,iru_i,uavg_i,kst_i,
     &                     el_i,bvf_i,tsigv_i,tsigw_i,symin_i,szmin_i,
     &                     zht_i,zmix_i,ix_i,iy_i,md_i,mhftsz_i,mtauly_i
      if(ios.ne.0) goto 999
      mhftsz=mhftsz_i
      mtauly=mtauly_i
      syh=300.0
      call setcsig(idopty_i,idoptz_i,iru_i,uavg_i,kst_i,el_i,bvf_i,
     &             tsigv_i,tsigw_i,symin_i,szmin_i,zht_i,zmix_i,
     &             ix_i,iy_i,md_i)
      write(*,'(i8,8(1x,i8),14(1x,es20.12))') icase,idoptys,idoptzs,
     &  irus,kstabs,mhftszs,ixcell,iycell,mdcell,uavgs,els,bvfs,
     &  tsigvs,tsigws,symins,szmins,thfty,sigty_in1,sigty_in2,
     &  sigty_in3,sigty_out1,sigty_out2,sigty_out3
      goto 30
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine sigty(sigy0,dxkm,dt,sigy,virty,virdy)
c-----------------------------------------------------------------------
c --- Deterministic SIGTY stub (the vendor SIGTY/SIGTZ themselves carry
c     the P7D parity evidence). The C++ test injects the identical formula
c     and records the same in/out pair.
      common/p7pdbg/sigty_in1,sigty_in2,sigty_in3,sigty_out1,sigty_out2,
     &              sigty_out3
      real sigy0,dxkm,dt,sigy,virty,virdy
      real sigty_in1,sigty_in2,sigty_in3,sigty_out1,sigty_out2
      real sigty_out3
      sigty_in1=sigy0
      sigty_in2=dxkm
      sigty_in3=dt
      sigy=sigy0+0.5*dxkm+0.1*dt
      virdy=sigy0*0.01
      virty=sigy0*0.5
      sigty_out1=sigy
      sigty_out2=virty
      sigty_out3=virdy
      return
      end
c-----------------------------------------------------------------------
      subroutine tauly(ldb,tsigv,tsigw,el,zmix,zht,tau)
c-----------------------------------------------------------------------
c --- Stub for the Lagrangian time scale (MTAULY=1 is off this deck's path).
      logical ldb
      real tsigv,tsigw,el,zmix,zht,tau
      write(*,*) 'P7P oracle: TAULY must not be called'
      stop 9
      end
